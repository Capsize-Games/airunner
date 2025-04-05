#!/bin/bash

# Function to handle virtualenv checks and installation
handle_virtualenv_installation() {
    # Check for existing virtualenv environments
    if [ -d "./venv" ]; then
        echo "Existing virtualenv environment found: venv"
        read -p "Do you want to use the 'venv' environment? (yes/no): " use_existing_venv
        if [ "$use_existing_venv" = "yes" ]; then
            source ./venv/bin/activate
            pip install --no-deps -e .
            deactivate
            return
        fi
    fi

    # Check for other virtualenv environments using lsvirtualenv
    existing_envs=$(lsvirtualenv -b 2>/dev/null)
    if [ -n "$existing_envs" ]; then
        echo "Other virtualenv environments found:"
        echo "$existing_envs"
        read -p "Which environment do you want to use? (leave blank to skip): " selected_env
        if [ -n "$selected_env" ]; then
            source ~/.virtualenvs/$selected_env/bin/activate
            pip install --no-deps -e .
            deactivate
            return
        fi
    fi

    # Ask if the user wants to use virtualenv
    read -p "No virtualenv found. Do you want to use virtualenv? (recommended) (yes/no): " use_virtualenv
    if [ "$use_virtualenv" = "yes" ]; then
        read -p "Enter the name for the new virtualenv (default: venv): " venv_name
        venv_name=${venv_name:-venv}
        python3 -m venv $venv_name
        source $venv_name/bin/activate
        pip install --no-deps -e .
        deactivate
    else
        pip install --no-deps -e .
    fi
}

# Display an option menu to the user
PS3='Please select an option: '
options=(
    "Setup xhost for Docker"
    "Install AI Runner scripts"
    "Install AI Runner locally (not recommended)"
    "Quit"
)

select opt in "${options[@]}"; do
    case $opt in
        "Setup xhost for Docker")
            if [ -f "$HOME/.docker.xauth" ]; then
                echo "Docker xauth file already exists. Skipping creation."
            else
                xhost +local:docker
                HOST_DISPLAY=$DISPLAY
                DOCKER_XAUTHORITY=$HOME/.docker.xauth
                touch $DOCKER_XAUTHORITY
                xauth nlist $HOST_DISPLAY | sed -e 's/^..../ffff/' | xauth -f $DOCKER_XAUTHORITY nmerge -
                chmod 644 $DOCKER_XAUTHORITY
            fi
            ;;
        "Install AI Runner scripts")
            handle_virtualenv_installation
            ;;
        "Install AI Runner locally (not recommended)")
            handle_virtualenv_installation
            ;;
        "Quit")
            break
            ;;
        *)
            echo "Invalid option $REPLY"
            ;;
    esac
    echo
    PS3='Please select another option or Quit: '
    REPLY=""
done