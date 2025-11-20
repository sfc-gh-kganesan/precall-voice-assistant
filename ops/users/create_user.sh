#!/bin/bash

# Check if username was provided as argument
if [ -n "$1" ]; then
    username="$1"
else
    # Prompt for username if not provided
    read -p "Enter username: " username
fi

# Check if username was provided
if [ -z "$username" ]; then
    echo "Error: Username cannot be empty"
    exit 1
fi

# Check if snow connection is provided
if [ -z "$CONNECTION" ]; then
    echo "Error: Connection cannot be empty. Please choose which Snow CLI connection to use by specifying CONNECTION=<connection>."
    exit 1
fi

# Check if the YAML file exists
if [ ! -f "${username}.yml" ]; then
    echo "Error: ${username}.yml not found"
    exit 1
fi

# Read variables from YAML file and build --variable arguments
variables=""
while IFS=': ' read -r key value; do
    # Skip empty lines and comments
    [[ -z "$key" || "$key" =~ ^# ]] && continue
    
    # Remove leading/trailing whitespace and quotes from value
    value=$(echo "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//")
    
    # Add to variables string
    variables="$variables --variable ${key}=${value}"
done < "${username}.yml"

# Prompt for temp password
read -p "Enter temp password: " temp_password

# Run the snow sql command
snow sql -f create_user.sql -c $CONNECTION --role ACCOUNTADMIN $variables --variable password=${temp_password}
