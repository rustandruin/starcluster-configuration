# Installs PyGrib and its dependencies
# TODO: assumes hadoop is installed @
# TODO: assumes java is installed @
# TODO: configure AWS for s3cmd

from starcluster import clustersetup
from starcluster.logger import log
import socket

class PyGribInstaller(clustersetup.DefaultClusterSetup):

    geos_dir = '/usr/local'

    def __init__(self):
        super(PyGribInstaller, self).__init__()
        log.debug("Installing PyGrib")

    def _install_sbt(self, node):
        instructions = [
            'echo "deb http://dl.bintray.com/sbt/debian /" | sudo tee -a /etc/apt/sources.list.d/sbt.list',
            'sudo apt-get update',
            'sudo apt-get -y --force-yes install sbt'
        ]
        node.ssh.execute(' && '.join(instructions))

    def _install_s3_and_boto(self, node):
        instructions = [
            "apt-get -y install s3cmd",
            "pip install boto"
        ]
        node.ssh.execute(' && '.join(instructions))

    def _install_ipython_notebook(self, node):
        instructions = [
            "apt-get -y install ipython ipython-notebook libfreetype6-dev libpng3",
            "pip install mock",
            "easy_install matplotlib",
            "apt-get -y install cython"
        ]
        node.ssh.execute(' && '.join(instructions))
        
    def _install_geos(self, node):
        instructions = [
            "wget http://download.osgeo.org/geos/geos-3.4.2.tar.bz2",
            "tar -xjvf geos-3.4.2.tar.bz2",
            "cd geos-3.4.2",
            "./configure",
            "make",
            "make install",
            "cd ..; rm -rf geos-3.4.2*"
        ]
        node.ssh.execute(' && '.join(instructions))

    def _install_hdf5(self, node):
        instructions = [
            "wget ftp://ftp.hdfgroup.org/HDF5/current/src/hdf5-1.8.15-patch1.tar.gz",
            "tar xzf hdf5-1.8.15-patch1.tar.gz",
            "cd hdf5-1.8.15-patch1",
            "./configure --prefix=/usr/local/hdf5 --enable-hl --enable-shared --enable-cxx",
            "make && make install",
            "cd ..", 
            "rm -rf hdf5*",
            "apt-get -y install libcurl4-gnutls-dev"
        ]
        node.ssh.execute(' && '.join(instructions))

    def _install_netcdf(self, node):
        instructions = [
            "wget ftp://ftp.unidata.ucar.edu/pub/netcdf/netcdf-4.3.3.tar.gz",
            "tar xzf netcdf-4.3.3.tar.gz",
            "cd netcdf-4.3.3",
            'CPPFLAGS="-I/usr/local/hdf5/include"  LDFLAGS="-L/usr/local/hdf5/lib" ./configure --prefix=/usr/local/netcdf-4 --enable-netcdf-4 --enable-shared',
            "make && make install",
            "cd ..",
            "rm -rf netcdf*"
        ]
        node.ssh.execute(' && '.join(instructions))

    def _install_pynetcdf4(self, node):
        instructions = [
            "wget https://netcdf4-python.googlecode.com/files/netCDF4-1.0.7.tar.gz",
            "tar xzf netCDF4-1.0.7.tar.gz",
            "cd netCDF4-1.0.7",
            "PATH=$PATH:/usr/local/netcdf-4/bin USE_NCCONFIG=1 python setup.py build",
            "PATH=$PATH:/usr/local/netcdf-4/bin USE_NCCONFIG=1 python setup.py install",
            "cd ..",
            "rm -rf netCDF*"
        ]
        node.ssh.execute(' && '.join(instructions))

    def _install_basemap(self, node):
        instructions = [
            "export GEOS_DIR=/usr/local",
            "wget -O basemap.tgz http://sourceforge.net/projects/matplotlib/files/matplotlib-toolkits/basemap-1.0.7/basemap-1.0.7.tar.gz/download",
            "tar -xzvf basemap.tgz",
            "cd basemap-1.0.7",
            "python setup.py build",
            "python setup.py install",
            "cd ..; rm -rf basemap*"
        ]
        node.ssh.execute(' && '.join(instructions))

    def _install_pyproj(self, node):
        instructions = [
            "git clone https://github.com/jswhit/pyproj.git",
            "cd pyproj",
            "python setup.py build",
            "python setup.py install",
            "cd ..; rm -rf pyproj"
        ]
        node.ssh.execute(' && '.join(instructions))

    def _install_grib_api(self, node):
        node.ssh.execute('apt-get -y install libgrib-api-dev')

    def _install_pygrib(self, node):
        self._install_grib_api(node)
        instructions = [
            "git clone https://github.com/jswhit/pygrib.git",
            "cd pygrib"
        ]
        node.ssh.execute(' && '.join(instructions))
        configfile = [
            "[directories]",
            "grib_api_dir=/usr/local"
        ]
        config_fh = node.ssh.remote_file("/root/pygrib/setup.cfg", 'w')
        config_fh.write("\n".join(configfile))
        config_fh.close()
        instructions = [
            "cd pygrib",
            "python setup.py build",
            "python setup.py install",
            "cd ..; rm -rf pygrib"
        ]
        node.ssh.execute(' && '.join(instructions))
    
    def _install_pydoop(self, node):
        instructions = [
            "export JAVA_HOME=/usr/lib/jvm/java-7-openjdk-amd64",
            "export HADOOP_HOME=/usr/local/hadoop",
            "pip install pydoop"
        ]
        node.ssh.execute(' && '.join(instructions))

    def _configure_ipython(self, master):
        master.ssh.execute('su -c "cd /home/ubuntu; ipython profile create pyspark" - ubuntu')
        profilefile = """\
c = get_config()
c.NotebookApp.ip='*'
c.NotebookApp.open_browser=False
c.NotebookApp.port=8880
        """
        profilefile_fh = master.ssh.remote_file("/home/ubuntu/.ipython/profile_pyspark/ipython_config.py", 'w')
        profilefile_fh.write(profilefile)
        profilefile_fh.close()
        startupfile = """\
import os
import sys

spark_home = os.environ.get('SPARK_HOME', None)
if not spark_home:
    raise ValueError('SPARK_HOME environment variable is not set')
sys.path.insert(0, os.path.join(spark_home, 'python'))
sys.path.insert(0, os.path.join(spark_home, 'python/lib/py4j-0.8.1-src.zip'))
execfile(os.path.join(spark_home, 'python/pyspark/shell.py'))  
"""
        startupfile_fh = master.ssh.remote_file("/home/ubuntu/.ipython/profile_pyspark/startup/00-pyspark-setup.py", 'w')
        startupfile_fh.write(startupfile)
        startupfile_fh.close()

        startupscript = """\
export JAVA_HOME=/usr/lib/jvm/java-7-openjdk-amd64
export PYSPARK_SUBMIT_ARGS='--master yarn pyspark-shell'
ipython notebook --profile=pyspark
"""
        startupscript_fh = master.ssh.remote_file("/home/ubuntu/startnb.sh", "w")
        startupscript_fh.write(startupscript)
        startupscript_fh.close()

        master.ssh.execute("chown -R ubuntu:ubuntu /home/ubuntu")


    def _open_ports(self, master):
        # figure out the ip address of the controlling starcluster computer in a cross platform manner
        # a la http://zeth.net/archive/2007/11/24/how-to-find-out-ip-address-in-python/
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('google.com', 80))
        myip = s.getsockname()[0] + "/24"
        s.close()

        ports = [8880]
        ec2 = master.ec2
        for group in master.cluster_groups:
            for port in ports:
                has_perm = ec2.has_permission(group, 'tcp', port, port, myip)
                if not has_perm:
                    ec2.conn.authorize_security_group(group_id=group.id, ip_protocol='tcp', from_port=port, to_port=port, cidr_ip=myip)

    def run(self, nodes, master, user, shell, volumes):
        aliases = [n.alias for n in nodes]

        log.info("Installing SBT")
        for node in nodes:
            self.pool.simple_job(self._install_sbt, (node), jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

        log.info("Installing S3 and Boto")
        for node in nodes:
            self.pool.simple_job(self._install_s3_and_boto, (node), jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))
        
        log.info("Installing Cython, IPython Notebook and Matplotlib")
        for node in nodes:
            self.pool.simple_job(self._install_ipython_notebook, (node), jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

        log.info("installing GEOS")
        for node in nodes:
            self.pool.simple_job(self._install_geos, (node), jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

        log.info("Installing Basemap")
        for node in nodes:
            self.pool.simple_job(self._install_basemap, (node), jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

        log.info("Installing PyProj")
        for node in nodes:
            self.pool.simple_job(self._install_pyproj, (node), jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

        log.info("Installing PyGrib")
        for node in nodes:
            self.pool.simple_job(self._install_pygrib, (node), jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

        log.info("Installing Pydoop")
        for node in nodes:
            self.pool.simple_job(self._install_pydoop, (node), jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

        log.info("Installing HDF5 and Libcurl")
        for node in nodes:
            self.pool.simple_job(self._install_hdf5, (node), jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

        log.info("Installing NetCDF-4-C")
        for node in nodes:
            self.pool.simple_job(self._install_netcdf, (node), jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

        log.info("Installing PyNetCDF4")
        for node in nodes:
            self.pool.simple_job(self._install_pynetcdf4, (node), jobid=node.alias)
        self.pool.wait(numtasks=len(nodes))

        log.info("Configuring IPython PySpark profile and startup script")
        self._configure_ipython(master)

        log.info("Opening port for IPython Notebook")
        self._open_ports(master)

        log.info("Don't forget to configure s3cmd with s3cmd --configure!")
