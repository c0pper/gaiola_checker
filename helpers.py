import os
import json

def save_to_json(name, code):
    data = {
        "name": name,
        "code": code
    }

    filename = f"{name.lower()}_{code}.json"
    filepath = os.path.join("bookings", filename)

    with open(filepath, 'w') as json_file:
        json.dump(data, json_file, indent=4)


def find_code_by_name(name):
    directory = "bookings"
    filename_prefix = name.lower() + "_"

    for filename in os.listdir(directory):
        if filename.startswith(filename_prefix):
            code = filename.split("_")[1]
            return code
    print("No booking file found")
    return None


def delete_booking_file(name, code):
    filename = f"{name.lower()}_{code}"
    filepath = os.path.join("bookings", filename)

    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    else:
        return False