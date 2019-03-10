import graphene

import ibis.schema
import profiles.schema


class Query(profiles.schema.Query, ibis.schema.Query, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query)
