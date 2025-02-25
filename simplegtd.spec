# See https://docs.fedoraproject.org/en-US/packaging-guidelines/Python/#_example_spec_file

%define debug_package %{nil}

%define _name simplegtd

%define mybuildnumber %{?build_number}%{?!build_number:1}

Name:           %{_name}
Version:        0.0.26
Release:        %{mybuildnumber}%{?dist}
Summary:        Manage your todo.txt task list using the Getting Things Done system.

License:        GPLv3+
URL:            https://github.com/Rudd-O/%{_name}
Source:         %{_name}-%{version}.tar.gz

BuildArch:      noarch
BuildRequires:  python3-devel, python3-setuptools python3-gobject
BuildRequires:  desktop-file-utils
BuildRequires:  coreutils
# Build test reqs
BuildRequires:  python3dist(pytest)
BuildRequires:  python3dist(mypy)
BuildRequires:  gtk3
BuildRequires:  libhandy >= 1.8.0
BuildRequires:  libhandy < 2.0

Requires:       gobject-introspection python3-gobject-base python3-pyxdg
Requires:       libhandy >= 1.8.0
Requires:       libhandy < 2.0

%global _description %{expand:
Simple GTD lets you manage your to-do list using the
Getting Things Done system.}

%description %_description

%prep
%autosetup -p1

%generate_buildrequires
%pyproject_buildrequires -t


%build
%pyproject_wheel


%install
%pyproject_install

mkdir -p %{buildroot}%{_datadir}/icons %{buildroot}%{_datadir}/applications
install src/%{_name}/data/icons/%{_name}.svg -t %{buildroot}%{_datadir}/icons
desktop-file-install --dir=%{buildroot}%{_datadir}/applications src/%{_name}/data/applications/%{_name}.desktop

%pyproject_save_files %{_name}
echo %{_bindir}/%{_name} >> %{pyproject_files}
echo %{_datadir}/icons/%{_name}.svg >> %{pyproject_files}
echo %{_datadir}/applications/%{_name}.desktop >> %{pyproject_files}


%check
%tox


%files -f %{pyproject_files}

%doc README.md


%changelog
* Wed Feb 21 2024 Manuel Amador <rudd-o@rudd-o.com> 0.0.26-1
- First RPM packaging release
