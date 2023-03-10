#!/bin/bash

# set -x
dbus_send_systemd(){

    local action=${1:-"StartUnit"}
    local target=${2:-"plymouth-quit.service"}


    dbus-send \
        --system \
        --dest=org.freedesktop.systemd1 \
        --type=method_call \
        --print-reply \
        /org/freedesktop/systemd1 \
        "org.freedesktop.systemd1.Manager.${action}" \
        string:"${target}" \
        string:"replace" \
    > /dev/null

}

get_ip_supervisor(){
    IP=$(curl -X GET -s --header "Content-Type:application/json" \
        "$BALENA_SUPERVISOR_ADDRESS/v1/device?apikey=$BALENA_SUPERVISOR_API_KEY" \
        | jq '.ip_address' \
        | sed 's/"//g')

    echo -e "\033[0;34mLocal IP address: \033[0;33m $IP \033[0m"
    echo -e "\033[0;34mHostname: \033[0;33m $HOSTNAME \033[0m"
    echo -e "\033[0;36mPoint your browser at \033[0;32mhttp://$HOSTNAME \033[0;36mor \033[0;32mhttp://$IP \033[0;36mto get started! \033[0m"
    echo -e "$(ip a)"
}



set -x
# quit the plymouth (balena logo) service so that we can see the TTY
dbus_send_systemd "StartUnit" "plymouth-quit.service"
# restart getty so something is listening
dbus_send_systemd "StartUnit" "getty@tty0.service"
echo "I have started"  > /dev/tty0
set +x

while true
do
    #Get the IP address from the supervisor
    output_tty=$(get_ip_supervisor)
    clear > /dev/tty0
    echo "${output_tty}" > /dev/tty0
    sleep 0.5
done


balena-idle
