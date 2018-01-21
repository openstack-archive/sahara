# execute_in_directory <directory> <command>
execute_in_directory() {
    local directory="$(readlink -f "$1")"; shift
    local cmd="$*"

    pushd "$directory" && eval "$cmd" && popd
}

# get_distro
get_distro() {
    echo "$DISTRO_NAME"
}

# download_apt_package <package> [version] [directory]
download_apt_package() {
    local package="$1"
    local version="${2:-}"
    local directory="${3:-$(pwd)}"
    local package_spec="$package${version:+=$version*}"

    execute_in_directory "$directory" apt-get --allow-unauthenticated download "$package_spec"
}

# download_yum_package <package> [version] [directory]
download_yum_package() {
    local package="$1"
    local version="${2:-}"
    local directory="${3:-$(pwd)}"
    local package_spec="$package${version:+-$version*}"

    yumdownloader --destdir "$directory" "$package_spec"
}

# download_package <package> [version] [directory] [distro]
download_package() {
    local package="$1"
    local version="${2:-}"
    local directory="${3:-$(pwd)}"
    local distro="${4:-$(get_distro)}"

    if [[ "$distro" == "ubuntu" ]]; then
        download_apt_package "$package" "$version" "$directory"
    elif [[ "$distro" == "centos" || "$distro" == "centos7" || "$distro" == "rhel" || "$distro" == "rhel7" ]]; then
        download_yum_package "$package" "$version" "$directory"
    fi
}

# get_packages <package_groups_file> <spec_file> [version_separator]
get_packages() {
    local package_groups_file="$1"
    local spec_file="$2"
    local version_separator="${3:-:}"

    python "$VERSIONS_PY" --separator "$version_separator" "$package_groups_file" "$spec_file"
}

# download_packages <package_groups_file> <spec_file> [directory] [distro]
download_packages() {
    local package_groups_file="$1"
    local spec_file="$2"
    local directory="${3:-$(pwd)}"
    local distro="${4:-$(get_distro)}"
    local version_separator=":"

    local packages="$(get_packages "$package_groups_file" "$spec_file" "$version_separator")"
    for package in $packages; do
        IFS="$version_separator" read -ra package_version <<< "$package"
        download_package "${package_version[@]}" "$directory" "$distro"
    done
}

# create_apt_repo <directory>
create_apt_repo() {
    local directory="$(readlink -f "$1")"
    local binary_dir="$directory/binary"
    local packages_gz="$binary_dir/Packages.gz"

    mkdir -p "$binary_dir"
    execute_in_directory "$directory" "dpkg-scanpackages -m . /dev/null | gzip -9c > $packages_gz"
}

# create_yum_repo <directory>
create_yum_repo() {
    local directory="$(readlink -f "$1")"

    createrepo "$directory"
}

# create_repo <directory> [distro]
create_repo() {
    local directory="$(readlink -f "$1")"
    local distro="${2:-$(get_distro)}"

    if [[ "$distro" == "ubuntu" ]]; then
        create_apt_repo "$directory"
    elif [[ "$distro" == "centos" || "$distro" == "centos7" || "$distro" == "rhel" || "$distro" == "rhel7" ]]; then
        create_yum_repo "$directory"
    fi
}

# add_apt_repo <repo_name> <repo_url>
add_apt_repo() {
    local repo_name="$1"
    local repo_url="$2"
    local repo="deb $repo_url"
    local repo_path="/etc/apt/sources.list.d/$repo_name.list"

    echo "$repo" > "$repo_path" && apt-get update
}

# add_yum_repo <repo_name> <repo_url>
add_yum_repo() {
    local repo_name="$1"
    local repo_url="$2"
    local repo_path="/etc/yum.repos.d/$repo_name.repo"

    cat > "$repo_path" << EOF
[$repo_name]
name=$repo_name
baseurl=$repo_url
enabled=1
gpgcheck=0
protect=1
EOF
    yum clean all && rm -rf /var/cache/yum/* && yum check-update
}

# add_repo <repo_name> <repo_url> [distro]
add_repo() {
    local repo_name="$1"
    local repo_url="$2"
    local distro="${3:-$(get_distro)}"

    if [[ "$distro" == "ubuntu" ]]; then
        add_apt_repo "$repo_name" "$repo_url"
    elif [[ "$distro" == "centos" || "$distro" == "centos7" || "$distro" == "rhel" || "$distro" == "rhel7" ]]; then
        add_yum_repo "$repo_name" "$repo_url"
    fi
}

# add_local_apt_repo <repo_name> <directory>
add_local_apt_repo() {
    local repo_name="$1"
    local directory="$(readlink -f "$2")"
    local repo_url="file:$directory binary/"

    add_apt_repo "$repo_name" "$repo_url"
}

# add_local_yum_repo <repo_name> <directory>
add_local_yum_repo() {
    local repo_name="$1"
    local directory="$(readlink -f "$2")"
    local repo_url="file://$directory"

    add_yum_repo "$repo_name" "$repo_url"
}

# add_local_repo <repo_name> <directory> [distro]
add_local_repo() {
    local repo_name="$1"
    local directory="$(readlink -f "$2")"
    local distro="${3:-$(get_distro)}"

    if [[ "$distro" == "ubuntu" ]]; then
        add_local_apt_repo "$repo_name" "$directory"
    elif [[ "$distro" == "centos" || "$distro" == "centos7" || "$distro" == "rhel" || "$distro" == "rhel7" ]]; then
        add_local_yum_repo "$repo_name" "$directory"
    fi
}

# remove_apt_repo <repo_name>
remove_apt_repo() {
    local repo_name="$1"
    local repo_path="/etc/apt/sources.list.d/$repo_name.list"

    rm "$repo_path" && apt-get update
}

# remove_yum_repo <repo_name>
remove_yum_repo() {
    local repo_name="$1"
    local repo_path="/etc/yum.repos.d/$repo_name.repo"

    rm "$repo_path"
}

# remove_repo <repo_name> [distro]
remove_repo() {
    local repo_name="$1"
    local distro="${2:-$(get_distro)}"

    if [[ "$distro" == "ubuntu" ]]; then
        remove_apt_repo "$repo_name"
    elif [[ "$distro" == "centos" || "$distro" == "centos7" || "$distro" == "rhel" || "$distro" == "rhel7" ]]; then
        remove_yum_repo "$repo_name"
    fi
}

# create_local_repo <repo_name> <repo_url> <package_groups_file> <spec_file> <directory>
create_local_repo() {
    local repo_name="$1"
    local repo_url="$2"
    local package_groups_file="$3"
    local spec_file="$4"
    local directory="$5"

    add_repo "$repo_name" "$repo_url"
    mkdir -p "$directory" && directory="$(readlink -f "$directory")"
    download_packages "$package_groups_file" "$spec_file" "$directory"
    remove_repo "$repo_name"
    create_repo "$directory"
}

# localize_repo <repo_name> <repo_url> <package_groups_file> <spec_file> <directory>
localize_repo() {
    local repo_name="$1"
    local repo_url="$2"
    local package_groups_file="$3"
    local spec_file="$4"
    local directory="$5"

    mkdir -p "$directory" && directory="$(readlink -f "$directory")"
    create_local_repo "$repo_name" "$repo_url" "$package_groups_file" "$spec_file" "$directory"
    add_local_repo "$repo_name" "$directory"
}
