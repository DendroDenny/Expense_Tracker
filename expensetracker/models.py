from django.db import models
from django.conf import settings
from django.db.models import Q


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    image = models.ImageField(upload_to='profile_pictures/', blank=True)

    def __str__(self):
        return f'{self.user.username} profile'


class Expense(models.Model):
    class Category(models.TextChoices):
        FOOD = 'food', 'Food'
        TRANSPORT = 'transport', 'Transport'
        SHOPPING = 'shopping', 'Shopping'
        BILLS = 'bills', 'Bills'
        OTHER = 'other', 'Other'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='expenses',
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.CharField(max_length=20, choices=Category.choices)
    date = models.DateField()
    note = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ('-date', '-pk')
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name='expense_amount_positive',
            ),
        ]

    def __str__(self):
        return f'{self.get_category_display()} expense: {self.amount}'


class MonthlyBudget(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='monthly_budgets',
    )
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=300000)

    class Meta:
        ordering = ('-year', '-month')
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'year', 'month'),
                name='unique_user_monthly_budget',
            ),
            models.CheckConstraint(
                condition=Q(month__gte=1) & Q(month__lte=12),
                name='monthly_budget_month_valid',
            ),
            models.CheckConstraint(
                condition=Q(amount__gte=0),
                name='monthly_budget_amount_nonnegative',
            ),
        ]

    def __str__(self):
        return f'{self.user.username} budget for {self.year}-{self.month:02}'
