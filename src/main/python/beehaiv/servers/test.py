import hug
from pony import orm
from beehaiv import api, models


@hug.extend_api()
def main_api():
    return [api]


api.db.bind(provider='sqlite', filename=':memory:')
api.db.generate_mapping(create_tables=True)

with orm.db_session():
    models.User(username='testuser', password='testpass', isadmin=True)
