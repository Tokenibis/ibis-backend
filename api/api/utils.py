def get_submodel(instance):
    for submodel in instance.__class__.__subclasses__():
        if submodel.objects.filter(pk=instance.pk).exists():
            return submodel
    return instance.__class__
