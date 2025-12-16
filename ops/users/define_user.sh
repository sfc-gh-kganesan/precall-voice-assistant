#!/bin/bash

# Prompt for user information
read -p "Enter LDAP user name: " ldap_username
read -p "Enter first name: " first_name
read -p "Enter last name: " last_name
read -p "Enter email address: " email_address

# Validate that all fields are provided
if [ -z "$ldap_username" ] || [ -z "$first_name" ] || [ -z "$last_name" ] || [ -z "$email_address" ]; then
    echo "Error: All fields are required"
    exit 1
fi

# Set the output filename
output_file="${ldap_username}.yml"

# Check if file already exists
if [ -f "$output_file" ]; then
    echo "Error: ${output_file} already exists"
    exit 1
fi

# Create the YAML file
cat > "$output_file" << EOF
---
login_name: ${ldap_username}
display_name: ${ldap_username}
first_name: ${first_name}
last_name: ${last_name}
email: ${email_address}
must_change_password: TRUE
default_warehouse: compute_wh
default_role: public
EOF

echo "Successfully created ${output_file}"

echo "To provision this user, please run:"
echo "CONNECTION=<AIFDE Connection> ./create_user.sh ${ldap_username}"
