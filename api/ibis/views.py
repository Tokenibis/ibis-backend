from rest_framework import generics, response, exceptions
from .models import IbisUser
from .serializers import LoginFormSerializer


class LoginView(generics.GenericAPIView):
    serializer_class = LoginFormSerializer

    def post(self, request, *args, **kwargs):
        print(request.user)
        print(request.auth)
        serializerform = self.get_serializer(data=request.data)
        if not serializerform.is_valid():
            raise exceptions.ParseError(detail="No valid values")
        token = request.data['token']
        # attempt to create a new ibis user if one doesn't exist
        # return the graph id
        return response.Response({'user_id': token})
