import graphene

import users.schema
import ibis.schema
import notifications.schema


class Query(
        users.schema.Query,
        ibis.schema.Query,
        notifications.schema.Query,
        graphene.ObjectType,
):
    pass


class Mutation(
        ibis.schema.Mutation,
        notifications.schema.Mutation,
        graphene.ObjectType,
):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
