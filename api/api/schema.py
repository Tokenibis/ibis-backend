import graphene

import ibis.schema
import users.schema


class Query(users.schema.Query, ibis.schema.Query, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query)
