import itertools

from graphene_django.registry import get_global_registry
from graphene_django.types import DjangoObjectType
from graphql.error import GraphQLError
from graphql_relay import from_global_id

_registry = get_global_registry()
_extra_register = {}


def _resolve_nodes(ids, graphene_type=None):
    pks = []
    invalid_ids = []
    used_type = graphene_type

    for graphql_id in ids:
        if not graphql_id:
            continue

        try:
            node_type, _id = from_global_id(graphql_id)
        except Exception:
            invalid_ids.append(graphql_id)
            continue

        if used_type:
            if str(used_type) != node_type:
                raise AssertionError(
                    "Must receive a {} id.".format(str(used_type))
                )

        used_type = node_type
        pks.append(_id)

    if invalid_ids:  # pragma: no cover
        raise GraphQLError(
            "Could not resolve to a node with the id list of '{}'.".format(
                invalid_ids,
            ),
        )

    return used_type, pks


def _resolve_graphene_type(type_name):
    for _, _type in itertools.chain(_extra_register.items(),
                                    _registry._registry.items()):
        if _type._meta.name == type_name:
            return _type
    else:  # pragma: no cover
        raise AssertionError("Could not resolve the type {}".format(type_name))


def register_type(graphene_type):
    """Register an extra type to be resolved in mutations."""
    assert issubclass(graphene_type, DjangoObjectType)
    _extra_register[graphene_type._meta.model] = graphene_type
    return graphene_type


def get_node(id, graphene_type=None):
    """Get a node given the relay id."""
    node_type, _id = from_global_id(id)
    if not graphene_type:
        graphene_type = _resolve_graphene_type(node_type)

    return graphene_type._meta.model.objects.get(pk=_id)


def get_nodes(ids, graphene_type=None):
    """Get a list of nodes.

    If the `graphene_type` argument is provided, the IDs will be validated
    against this type. If the type was not provided, it will be looked up in
    the Graphene's registry.

    Raises an error if not all IDs are of the same type.
    """
    nodes_type, pks = _resolve_nodes(ids, graphene_type)

    # If `graphene_type` was not provided, check if all resolved types are
    # the same. This prevents from accidentally mismatching IDs of different
    # types.
    if nodes_type and not graphene_type:
        graphene_type = _resolve_graphene_type(nodes_type)

    nodes = list(graphene_type._meta.model.objects.filter(pk__in=pks))
    nodes.sort(key=lambda e: pks.index(str(e.pk)))  # preserve order in pks

    if not nodes:  # pragma: no cover
        raise GraphQLError(
            "Could not resolve to a node with the id list of '{}'.".format(
                ids,
            ),
        )

    nodes_pk_list = [str(node.pk) for node in nodes]
    for pk in pks:
        if pk not in nodes_pk_list:  # pragma: no cover
            raise AssertionError(
                "There is no node of type {} with pk {}".format(
                    graphene_type,
                    pk,
                )
            )

    return nodes
