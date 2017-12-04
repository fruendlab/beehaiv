import hug
import api


@hug.extend_api()
def main_api():
    return [api]


api.db.bind(provider='sqlite', filename=':memory:')
api.db.generate_mapping(create_tables=True)
