import xml.etree.ElementTree as ET
import os
import sys

def parse_mtputty_xml(xml_file):
    """Parse MTPuTTY XML file and extract session information."""
    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
        sessions = []

        # Find the Putty section under Servers
        putty_section = root.find('.//Putty')
        if putty_section is None:
            print("Warning: No Putty section found in XML. Trying to parse as direct structure...")
            putty_section = root

        def parse_node(node, parent_folder=""):
            session = node.find('.//SavedSession')
            if session is not None:
                display_name = node.find('.//DisplayName')
                display_name = display_name.text if display_name is not None else 'Unknown'
                
                server_name = node.find('.//ServerName')
                server_name = server_name.text if server_name is not None else ''
                
                port = node.find('.//Port')
                port = port.text if port is not None else '22'
                
                username = node.find('.//UserName')
                username = username.text if username is not None else ''
                
                password = node.find('.//Password')
                password = password.text if password is not None else ''
                
                # Get CLParams which might contain additional connection info
                cl_params = node.find('.//CLParams')
                cl_params = cl_params.text if cl_params is not None else ''
                
                # Get script information
                script_node = node.find('.//Script')
                script_lines = []
                if script_node is not None:
                    for line in script_node:
                        if line.text:
                            script_lines.append(line.text)

                # Fix default port
                if port == '0':
                    port = '22'

                # Extract actual host from server name or CLParams
                actual_host = extract_host_from_connection_string(server_name, cl_params)
                actual_username = extract_username_from_connection_string(server_name, cl_params, username)

                sessions.append({
                    'name': display_name,
                    'host': actual_host,
                    'port': port,
                    'username': actual_username,
                    'password': password,
                    'parent_folder': parent_folder,
                    'server_name': server_name,
                    'cl_params': cl_params,
                    'script_lines': script_lines
                })

            # Recursively parse child nodes
            for child_node in node.findall('./Node'):  # Direct children only
                if child_node.get('Type') == "0":  # Folder
                    folder_display = child_node.find('./DisplayName')
                    if folder_display is not None:
                        folder_name = folder_display.text
                        new_parent_folder = f"{parent_folder}/{folder_name}" if parent_folder else folder_name
                        parse_node(child_node, new_parent_folder)
                elif child_node.get('Type') == "1":  # Session
                    parse_node(child_node, parent_folder)

        # Start parsing from all top-level nodes in the Putty section
        for server in putty_section.findall('./Node'):
            if server.get('Type') == "0":  # Folder
                folder_display = server.find('./DisplayName')
                if folder_display is not None:
                    folder_name = folder_display.text
                    parse_node(server, folder_name)
            elif server.get('Type') == "1":  # Direct session
                parse_node(server, "")

        return sessions
    
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: XML file '{xml_file}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

def extract_host_from_connection_string(server_name, cl_params):
    """Extract the actual host from complex connection strings."""
    # Priority: CLParams format like "192.0.2.10 -l user_a -pw *****"
    if cl_params and '@' not in cl_params:
        # Standard CLParams format
        parts = cl_params.split()
        if parts:
            return parts[0]  # First part is usually the host
    
    # Check server_name for patterns like "ACCOUNT_ID@jump_user@192.0.2.20@198.51.100.30"
    if server_name:
        if '@' in server_name:
            parts = server_name.split('@')
            if len(parts) >= 3:
                # Format: user@proxyuser@host@proxy
                return parts[2]  # The host part
            elif len(parts) == 2:
                # Format: user@host
                return parts[1]
        else:
            # Direct host
            return server_name
    
    return server_name or 'unknown'

def extract_username_from_connection_string(server_name, cl_params, username):
    """Extract the actual username from connection strings."""
    # Check CLParams first
    if cl_params and '-l ' in cl_params:
        # Extract username from "-l username" pattern
        parts = cl_params.split('-l ')
        if len(parts) > 1:
            user_part = parts[1].split()[0]  # Get first word after -l
            return user_part
    
    # Check if username is already provided
    if username:
        return username
    
    # Check server_name for patterns like "ACCOUNT_ID@jump_user@192.0.2.20@198.51.100.30"
    if server_name and '@' in server_name:
        parts = server_name.split('@')
        if len(parts) >= 3:
            # Format: user@proxyuser@host@proxy - use proxyuser
            return parts[1]
        elif len(parts) == 2:
            # Format: user@host
            return parts[0]
    
    return username or ''

def create_mobaxterm_session_string(session):
    """Create MobaXterm session string with proper formatting based on latest model."""
    ip_address = session['host']
    username = session['username']
    password = session['password']
    port = session['port']
    session_name = session['name']
    server_name = session['server_name']
    
    # Extract the last part of IP for display name (e.g., "2.20" from "192.0.2.20")
    ip_parts = ip_address.split('.')
    if len(ip_parts) >= 2:
        ip_suffix = f"{ip_parts[-2]}.{ip_parts[-1]}"
    else:
        ip_suffix = ip_address
    
    # Create session display name - if session name already contains IP info, use as-is
    # Otherwise, format as "SessionName - IP_suffix"
    if any(part in session_name for part in ip_parts[-2:]) or ip_suffix in session_name:
        session_display = session_name
    else:
        session_display = f"{session_name} - {ip_suffix}"
    
    # Determine the connection string and username bracket based on the model
    if server_name and '@' in server_name:
        # For multi-hop connections like "ACCOUNT_ID@jump_user@192.0.2.20@198.51.100.30"
        connection_string = server_name
        # Extract the first part as username for bracket
        username_for_bracket = server_name.split('@')[0] if server_name else username
    else:
        # For direct connections
        connection_string = ip_address
        username_for_bracket = username
    
    # Build the session string using the correct MobaXterm format from the model
    # Format: SessionName= #97#0%ConnectionString%port%[username]%%-1%-1%%%%%0%0%0%%%-1%0%0%0%%1080%%0%0%1%%0%%%%0%-1%-1%0%%#MobaFont%10%0%0%-1%15%236,236,236%30,30,30%180,180,192%0%-1%0%%xterm%-1%0%_Std_Colors_0_%80%24%0%1%-1%<none>%%0%0%-1%0%#0# #-1
    session_string = f"{session_display}= #97#0%{connection_string}%{port}%[{username_for_bracket}]%%-1%-1%%%%%0%0%0%%%-1%0%0%0%%1080%%0%0%1%%0%%%%0%-1%-1%0%%#MobaFont%10%0%0%-1%15%236,236,236%30,30,30%180,180,192%0%-1%0%%xterm%-1%0%_Std_Colors_0_%80%24%0%1%-1%<none>%%0%0%-1%0%#0# #-1"
    
    return session_string

def create_mobaxterm_ini(sessions, ini_file):
    """Create MobaXterm .mxtsessions file from parsed sessions."""
    try:
        with open(ini_file, 'w') as configfile:
            # Write main bookmarks section
            configfile.write("[Bookmarks]\n")
            configfile.write("SubRep=\n")
            configfile.write("ImgNum=42\n")
            configfile.write("\n")
            
            bookmark_count = 1
            
            # Build a tree structure to understand folder hierarchy
            folder_tree = {}
            root_sessions = []
            
            # First pass: organize sessions and build folder structure
            for session in sessions:
                if not session['parent_folder']:
                    root_sessions.append(session)
                else:
                    folder_path = session['parent_folder']
                    # Convert forward slashes to backslashes for MobaXterm format
                    folder_path_moba = folder_path.replace('/', '\\')
                    path_parts = folder_path.split('/')
                    
                    # Build nested structure
                    current_level = folder_tree
                    for i, part in enumerate(path_parts):
                        if part not in current_level:
                            # Create MobaXterm-style path with backslashes
                            moba_path_parts = folder_path.split('/')[:i+1]
                            moba_full_path = '\\'.join(moba_path_parts)
                            current_level[part] = {
                                'sessions': [],
                                'subfolders': {},
                                'full_path': moba_full_path
                            }
                        current_level = current_level[part]['subfolders']
                    
                    # Add session to the final folder
                    target_folder = folder_tree
                    for part in path_parts[:-1]:
                        target_folder = target_folder[part]['subfolders']
                    target_folder[path_parts[-1]]['sessions'].append(session)

            def write_folders_and_sessions(folder_dict, level=0):
                nonlocal bookmark_count
                
                for folder_name, folder_data in folder_dict.items():
                    folder_full_path = folder_data['full_path']
                    
                    # Calculate ImgNum based on the model patterns
                    if level == 0:  # Top level folders (like "ATOM Store App")
                        img_num = 31
                    elif level == 1:  # Second level folders (like "Production - Direct", "Staging - CybarArk")
                        img_num = 33
                    else:  # Deeper levels
                        img_num = 33
                    
                    # Write folder bookmark section
                    configfile.write(f"[Bookmarks_{bookmark_count}]\n")
                    configfile.write(f"SubRep={folder_full_path}\n")
                    configfile.write(f"ImgNum={img_num}\n")
                    
                    # Write all sessions in this folder
                    for session in folder_data['sessions']:
                        configfile.write(create_mobaxterm_session_string(session) + "\n")
                    
                    configfile.write("\n")  # Add blank line after each section
                    bookmark_count += 1
                    
                    # Recursively process subfolders
                    if folder_data['subfolders']:
                        write_folders_and_sessions(folder_data['subfolders'], level + 1)

            # Write the complete folder structure
            write_folders_and_sessions(folder_tree)
            
            # Write root level sessions
            for session in root_sessions:
                configfile.write(f"[Bookmarks_{bookmark_count}]\n")
                configfile.write(f"SubRep=\n")  # Root level
                configfile.write(f"ImgNum=42\n")  # Root sessions use ImgNum=42
                configfile.write(create_mobaxterm_session_string(session) + "\n")
                configfile.write("\n")
                bookmark_count += 1

        # Print conversion summary
        print(f"Successfully converted {len(sessions)} sessions from MTPuTTY to MobaXterm.")
        
        # Count sessions by folder
        folder_counts = {}
        sessions_with_passwords = 0
        for session in sessions:
            folder = session['parent_folder'] if session['parent_folder'] else 'Root'
            folder_counts[folder] = folder_counts.get(folder, 0) + 1
            if session['password']:
                sessions_with_passwords += 1
        
        print(f"Sessions with passwords: {sessions_with_passwords}")
        print(f"Folder breakdown:")
        for folder, count in sorted(folder_counts.items()):
            print(f"  - {folder}: {count} sessions")
        
        print(f"Output file created: {ini_file}")
        print("\nNote: Import the .mxtsessions file into MobaXterm:")
        print("1. Open MobaXterm")
        print("2. Go to Settings → Configuration → Bookmark settings")
        print("3. Click 'Import bookmarks from file'")
        print("4. Select the generated .mxtsessions file")
        
    except Exception as e:
        print(f"Error creating MobaXterm file: {e}")
        sys.exit(1)

def convert_mtputty_to_mobaxterm(mtputty_file, mobaxterm_file):
    """Convert MTPuTTY XML file to MobaXterm sessions file."""
    sessions = parse_mtputty_xml(mtputty_file)
    create_mobaxterm_ini(sessions, mobaxterm_file)

def get_xml_file_path():
    """Get XML file path from user input with validation."""
    while True:
        xml_file = input("Please enter the path to your MTPuTTY XML file: ").strip()
        
        # Remove quotes if user entered them
        xml_file = xml_file.strip('"\'')
        
        if not xml_file:
            print("Error: Please enter a valid file path.")
            continue
            
        if not os.path.exists(xml_file):
            print(f"Error: File '{xml_file}' does not exist. Please try again.")
            continue
            
        if not xml_file.lower().endswith('.xml'):
            print("Warning: The file doesn't have a .xml extension. Continue anyway? (y/n): ", end='')
            if input().lower() not in ['y', 'yes']:
                continue
                
        return xml_file

def main():
    """Main function to handle file input and conversion."""
    print("MTPuTTY to MobaXterm Converter")
    print("=" * 35)
    
    # Get XML file path from user
    xml_file = get_xml_file_path()
    
    # Create output file in the same directory as input file
    xml_dir = os.path.dirname(xml_file)
    xml_basename = os.path.splitext(os.path.basename(xml_file))[0]
    output_file = os.path.join(xml_dir, f"{xml_basename}_converted.mxtsessions")
    
    print(f"\nInput file: {xml_file}")
    print(f"Output file: {output_file}")
    print("\nConverting...")
    
    # Perform conversion
    convert_mtputty_to_mobaxterm(xml_file, output_file)
    
    print("\nConversion completed successfully!")
    print(f"You can now import '{output_file}' into MobaXterm.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nConversion cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
