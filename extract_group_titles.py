import requests

# Function to fetch M3U playlist and extract country group names
def get_country_groups(m3u_url):
    try:
        # Fetch the M3U playlist from the provided URL
        response = requests.get(m3u_url)
        response.raise_for_status()  # Raise an exception for any non-2xx status codes
        
        # Split the M3U playlist into lines
        lines = response.text.splitlines()
        
        # Set to hold unique country groups (to avoid duplicates)
        country_groups = set()
        
        # Iterate through each line to find group names in the EXTINF lines
        for line in lines:
            if line.startswith("#EXTINF"):
                # Extract the group-title information, which indicates the country or group
                if 'group-title' in line:
                    # Find the part of the line that contains the group title
                    start = line.find('group-title="') + len('group-title="')
                    end = line.find('"', start)
                    group_title = line[start:end]
                    
                    # Add the group (country) to the set
                    country_groups.add(group_title)
        
        # Return a sorted list of unique country groups
        return sorted(list(country_groups))
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching M3U playlist: {e}")
        return []

# Example usage
m3u_url = "https://starlite.best/api/list/USERNAME GOES HERE/PASSWORD GOES HERE/m3u8/livetv"  # Replace with your actual M3U URL
country_list = get_country_groups(m3u_url)

# Print the list of country groups
if country_list:
    print("Country Groups found in M3U playlist:")
    for country in country_list:
        print(country)
else:
    print("No country groups found.")

