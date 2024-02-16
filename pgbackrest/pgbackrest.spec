%global debug_package %{nil}
%global pgmajorversion 16
%global pginstdir /usr/pgsql-16

Summary:        Reliable PostgreSQL Backup & Restore
Name:           percona-pgbackrest
Version:        %{version}
Release:        1%{dist}
License:        MIT
Group:          Applications/Databases
URL:            http://www.pgbackrest.org
Source:         %{name}-%{version}.tar.gz
Source1:        pgbackrest.conf
Source2:	pgbackrest-tmpfiles.d
Source3:	pgbackrest.logrotate
Source4:	pgbackrest.service
BuildRequires:	openssl-devel zlib-devel percona-postgresql%{pgmajorversion}-devel
BuildRequires:	libzstd-devel libxml2-devel libyaml-devel libssh2-devel

%if 0%{?fedora} >= 37 || 0%{?rhel} >= 8
Requires:	lz4-libs libzstd libssh2
BuildRequires:	lz4-devel bzip2-devel
%endif
%if 0%{?rhel} && 0%{?rhel} <= 7
Requires:	lz4 libzstd libssh2
BuildRequires:	lz4-devel bzip2-devel
%endif
%if 0%{?suse_version} && 0%{?suse_version} <= 1499
Requires:	liblz4-1_7 libzstd1 libssh2-1
BuildRequires:	liblz4-devel libbz2-devel
%endif
%if 0%{?suse_version} && 0%{?suse_version} >= 1500
Requires:	liblz4-1 libzstd1 libssh2-1
BuildRequires:	liblz4-devel libbz2-devel
%endif

Requires:	postgresql-libs
Requires(pre):	/usr/sbin/useradd /usr/sbin/groupadd

BuildRequires:		systemd, systemd-devel
# We require this to be present for %%{_prefix}/lib/tmpfiles.d
Requires:		systemd
%if 0%{?suse_version}
%if 0%{?suse_version} >= 1315
Requires(post):		systemd-sysvinit
%endif
%else
Requires(post):		systemd-sysv
Requires(post):		systemd
Requires(preun):	systemd
Requires(postun):	systemd
%endif

Epoch:		1
Packager:       Percona Development Team <https://jira.percona.com>
Vendor:         Percona, LLC

%description
pgBackRest aims to be a simple, reliable backup and restore system that can
seamlessly scale up to the largest databases and workloads.

Instead of relying on traditional backup tools like tar and rsync, pgBackRest
implements all backup features internally and uses a custom protocol for
communicating with remote systems. Removing reliance on tar and rsync allows
for better solutions to database-specific backup challenges. The custom remote
protocol allows for more flexibility and limits the types of connections that
are required to perform a backup which increases security.

%prep
%setup -q -n %{name}-%{version}

%build
pushd src
export CPPFLAGS='-I %{pginstdir}/include'
export PATH=%{pginstdir}/bin/:$PATH
export LDFLAGS='-L%{pginstdir}/lib'
%configure
%{__make}
popd

%install
%{__install} -D -d -m 0755 %{buildroot}%{perl_vendorlib} %{buildroot}%{_bindir}
%{__install} -D -d -m 0700 %{buildroot}/%{_sharedstatedir}/pgbackrest
%{__install} -D -d -m 0700 %{buildroot}/var/log/pgbackrest
%{__install} -D -d -m 0700 %{buildroot}/var/spool/pgbackrest
%{__install} -D -d -m 0755 %{buildroot}%{_sysconfdir}
%{__install} %{SOURCE1} %{buildroot}/%{_sysconfdir}/pgbackrest.conf
%{__cp} -a src/pgbackrest %{buildroot}%{_bindir}/pgbackrest

# Install logrotate file:
%{__install} -p -d %{buildroot}%{_sysconfdir}/logrotate.d
%{__install} -p -m 644 %{SOURCE3} %{buildroot}%{_sysconfdir}/logrotate.d/pgbackrest

# ... and make a tmpfiles script to recreate it at reboot.
%{__mkdir} -p %{buildroot}/%{_tmpfilesdir}
%{__install} -m 0644 %{SOURCE2} %{buildroot}/%{_tmpfilesdir}/pgbackrest.conf

# Install unit file:
%{__install} -d %{buildroot}%{_unitdir}
%{__install} -m 644 %{SOURCE4} %{buildroot}%{_unitdir}/pgbackrest.service

%pre
%{__install} -d -m 700 /var/lib/pgsql/
groupadd -g 26 -o -r postgres >/dev/null 2>&1 || :
useradd -M -g postgres -o -r -d /var/lib/pgsql -s /bin/bash \
	-c "PostgreSQL Server" -u 26 postgres >/dev/null 2>&1 || :
%{__chown} postgres: /var/lib/pgsql

%post
if [ $1 -eq 1 ] ; then
   /bin/systemctl daemon-reload >/dev/null 2>&1 || :
   %if 0%{?suse_version}
   %if 0%{?suse_version} >= 1315
   %service_add_pre pgbackrest}.service
   %endif
   %else
   %systemd_post pgbackrest.service
   %endif
fi

%preun
if [ $1 -eq 0 ] ; then
	# Package removal, not upgrade
	/bin/systemctl --no-reload disable %{name}.service >/dev/null 2>&1 || :
	/bin/systemctl stop %{name}.service >/dev/null 2>&1 || :
fi

%postun
/bin/systemctl daemon-reload >/dev/null 2>&1 || :

if [ $1 -ge 1 ] ; then
	# Package upgrade, not uninstall
	/bin/systemctl try-restart %{name}.service >/dev/null 2>&1 || :
fi

%files
%defattr(-,root,root)
%license LICENSE
%{_bindir}/pgbackrest
%config(noreplace) %attr (644,root,root) %{_sysconfdir}/pgbackrest.conf
%config(noreplace) %{_sysconfdir}/logrotate.d/pgbackrest
%{_tmpfilesdir}/pgbackrest.conf
%{_unitdir}/pgbackrest.service
%attr(-,postgres,postgres) /var/log/pgbackrest
%attr(-,postgres,postgres) %{_sharedstatedir}/pgbackrest
%attr(-,postgres,postgres) /var/spool/pgbackrest

%changelog
* Tue Jul 16 2019  Evgeniy Patlan <evgeniy.patlan@percona.com> - 2.16.1
- First build of pgbackrest for Percona.
