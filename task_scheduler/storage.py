import json

class Storage:
    @staticmethod
    def save(file_path, data):

        with open(file_path, "w") as file:

            json.dump(data, file, indent=4)

    @staticmethod
    def load(file_path):

        with open(file_path, "r") as file:

            return json.load(file)
