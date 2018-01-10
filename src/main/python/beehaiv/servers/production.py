import os
import hug
from pony import orm
from beehaiv import api, models


@hug.extend_api()
def main_api():
    return [api]


api.db.bind(provider='sqlite',
            filename=os.environ['BEEHAIV_STORAGE'],
            create_db=True)
api.db.generate_mapping(create_tables=True)

admin_user, admin_pass = os.environ['BEEHAIV_ADMIN'].split(':')
with orm.db_session():
    user = models.User.get(username=admin_user)
    if not user:
        models.User(username=admin_user,
                    password=admin_pass,
                    isadmin=True)
