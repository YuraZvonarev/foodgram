from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Subscription, User
from .serializers import SubscriptionSerializer, UserSerializer


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=False,
            methods=['get'],
            permission_classes=[permissions.IsAuthenticated])
    def subscriptions(self, request):
        subs = Subscription.objects.filter(user=request.user)
        page = self.paginate_queryset(subs)
        if page:
            serializer = SubscriptionSerializer(
                page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
        serializer = SubscriptionSerializer(
            subs, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request, pk=None):
        author = get_object_or_404(User, pk=pk)
        if request.method == 'POST':
            if request.user == author:
                return Response(
                    {'error': 'Нельзя подписаться на себя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            sub, created = Subscription.objects.get_or_create(
                user=request.user, author=author)
            if not created:
                return Response({'error': 'Уже подписан'},
                                status=status.HTTP_400_BAD_REQUEST)
            serializer = SubscriptionSerializer(
                sub, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            Subscription.objects.filter(
                user=request.user, author=author).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
