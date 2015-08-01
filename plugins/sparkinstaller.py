# Installs Spark
# TODO: support adding and removing nodes 
# TODO: check for if spark already installed: if so, just 
# need to update the slaves file
# NB: HADOOP_CONF_DIR and SPARK_CLASSPATH are hardcoded
# CAVEAT: as is, Spark will be broken if you change the number
# nodes without deleting spark and rerunning this setup plugin

from starcluster import clustersetup
from starcluster.logger import log

class SparkInstaller(clustersetup.DefaultClusterSetup):

    spark_home = '/opt/Spark'
    spark_source = "http://www.carfab.com/apachesoftware/spark/spark-1.4.0/spark-1.4.0-bin-without-hadoop.tgz"
    spark_directory = 'spark-1.4.0-bin-without-hadoop'
    spark_profile = '/etc/profile.d/spark.sh'

    def __init__(self, hadoopconfdir = "/usr/local/hadoop/etc/hadoop", sparkclasspath ="`cat /home/ubuntu/hadoop_classpath`" ):
        super(SparkInstaller, self).__init__()
        self._hadoopconfdir = hadoopconfdir
        self._sparkclasspath = sparkclasspath

    def _isinstalledq(self, node):
        return node.ssh.path_exists(self.spark_home)

    def _install_spark(self, node):
        if not self._isinstalledq(node):
            log.info("...installing on %s" % node.alias)
            instructions = [
                "wget -O spark.tgz %s" % self.spark_source,
                "tar xvf spark.tgz",
                "rm spark.tgz",
                "mv %s %s" % (self.spark_directory, self.spark_home)
            ]
            node.ssh.execute(' && '.join(instructions))
            log.info("...done installing on %s" % node.alias)

    def _open_ports(self, master):
        ports = [8088, 8042]
        ec2 = master.ec2
        for group in master.cluster_groups:
            for port in ports:
                has_perm = ec2.has_permission(group, 'tcp', port, port, '0.0.0.0/0')
                if not has_perm:
                    ec2.conn.authorize_security_group(group_id=group.id, ip_protocol='tcp', from_port=port, to_port=port, cidr_ip='0.0.0.0/0')

    def run(self, nodes, master, user, shell, volumes):
        log.info("Installing Spark")

        aliases = [n.alias for n in nodes]

        for node in nodes:
            self.pool.simple_job(self._install_spark, (node), jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

        log.info("...writing conf/slaves file to all nodes")
        for node in nodes:
            slaves_conf = node.ssh.remote_file("%s/conf/slaves" % self.spark_home, 'w')
            slaves_conf.write('\n'.join(aliases) + '\n')
            slaves_conf.close()
            slaves_profile = node.ssh.remote_file("%s" % self.spark_profile, 'w')
            profile_settings = [
                "export SPARK_HOME=%s" % self.spark_home,
                "export PATH=$PATH:$SPARK_HOME/bin"
            ]
            slaves_profile.write('\n'.join(profile_settings))
            slaves_profile.close()

        log.info("...writing spark-env script to all nodes")
        for node in nodes:
            sparkenv_conf = node.ssh.remote_file("%s/conf/spark-env.sh" % self.spark_home, 'w')
            sparkenv_settings = [
                "#!/usr/bin/env bash",
                "export HADOOP_CONF_DIR={0}".format(self._hadoopconfdir),
                "export SPARK_CLASSPATH={0}".format(self._sparkclasspath)
            ]
            sparkenv_conf.write('\n'.join(sparkenv_settings))

        # since you're starting spark as ubuntu, just use the start and stop all scripts in the spark directory
        """
        log.info("...writing start/stopspark scripts to /home")
        startspark = [
            "#!/usr/bin/env bash",
            "MASTER=%s" % master.alias,
            'ssh $MASTER "(cd %s; ./sbin/start-master.sh)"' % self.spark_home,
            'ssh $MASTER "(cd %s; ./sbin/start-slaves.sh)"' % self.spark_home
        ]
        startspark_file = master.ssh.remote_file("/home/startspark.sh", "w")
        startspark_file.write("\n".join(startspark))
        startspark_file.close()

        stopspark = [
            "#!/usr/bin/env bash",
            "MASTER=%s" % master.alias,
            'ssh $MASTER "(cd %s; ./sbin/stop-slaves.sh)"' % self.spark_home,
            'ssh $MASTER "(cd %s; ./sbin/stop-master.sh)"' % self.spark_home
        ]
        stopspark_file = master.ssh.remote_file("/home/stopspark.sh", "w")
        stopspark_file.write("\n".join(stopspark))
        stopspark_file.close()
        """

        log.info("...opening ports")
        self._open_ports(master)

        log.info("...changing owner of SPARK_HOME to ubuntu")
        for node in nodes:
            node.ssh.execute("chown -R ubuntu:ubuntu {0}".format(self.spark_home))

        log.info("DON'T forget to create {0} containing the hadoop classpath".format(self._sparkclasspath))

