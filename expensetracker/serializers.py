from rest_framework import serializers

from .models import Expense


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = ('id', 'amount', 'category', 'date', 'note')
        read_only_fields = ('id',)

    def validate_amount(self, amount):
        if amount <= 0:
            raise serializers.ValidationError('Amount must be greater than zero.')
        return amount
