from datetime import date
from decimal import Decimal

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages
from django.db.models import Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import ExpenseForm, MonthlyBudgetForm, ProfileForm, ProfilePictureForm
from .models import Expense, MonthlyBudget, Profile


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('home')

    return render(request, 'expensetracker/login.html', {'form': form})


@login_required(login_url='login')
def home(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    action = request.POST.get('action') if request.method == 'POST' else None
    if request.method == 'POST' and not action and 'username' in request.POST:
        action = 'profile'
    form = ProfileForm(
        request.POST if action == 'profile' else None,
        instance=request.user,
    )
    picture_form = ProfilePictureForm(
        request.POST if action == 'profile' else None,
        request.FILES if action == 'profile' else None,
        instance=profile,
    )
    if action == 'profile' and form.is_valid() and picture_form.is_valid():
        old_image = profile.image
        form.save()
        picture_form.save()
        if old_image and (not profile.image or old_image.name != profile.image.name):
            old_image.delete(save=False)
        messages.success(request, 'Your profile has been updated.')
        return redirect('home')

    today = timezone.localdate()
    month_value = (
        request.GET.get('month')
        or request.POST.get('month')
        or f'{today.year:04}-{today.month:02}'
    )
    try:
        selected_year, selected_month = (
            int(part) for part in month_value.split('-', maxsplit=1)
        )
        selected_date = date(selected_year, selected_month, 1)
    except (TypeError, ValueError):
        selected_date = date(today.year, today.month, 1)
    if not 1900 <= selected_date.year <= 9998:
        selected_date = date(today.year, today.month, 1)

    next_month = date(
        selected_date.year + (selected_date.month == 12),
        selected_date.month % 12 + 1,
        1,
    )
    previous_month = date(
        selected_date.year - (selected_date.month == 1),
        (selected_date.month - 2) % 12 + 1,
        1,
    )
    next_month_value = next_month.strftime('%Y-%m')
    previous_month_value = previous_month.strftime('%Y-%m')
    monthly_budget, _ = MonthlyBudget.objects.get_or_create(
        user=request.user,
        year=selected_date.year,
        month=selected_date.month,
        defaults={'amount': Decimal('300000.00')},
    )

    expense = None
    if action == 'expense' and request.POST.get('expense_id'):
        expense = get_object_or_404(
            Expense,
            pk=request.POST['expense_id'],
            user=request.user,
        )
    expense_form = ExpenseForm(
        request.POST if action == 'expense' and expense is None else None,
        instance=expense,
        initial={'date': today} if expense is None else None,
    )
    edit_form = ExpenseForm(
        request.POST if action == 'expense' and expense is not None else None,
        instance=expense,
        auto_id='edit_%s',
    )
    budget_form = MonthlyBudgetForm(
        request.POST if action == 'budget' else None,
        instance=monthly_budget,
        auto_id='budget_%s',
    )

    if action == 'expense':
        submitted_form = edit_form if expense is not None else expense_form
        if submitted_form.is_valid():
            saved_expense = submitted_form.save(commit=False)
            saved_expense.user = request.user
            saved_expense.save()
            messages.success(request, 'Expense saved.')
            return redirect(f'{request.path}?month={selected_date:%Y-%m}')
    elif action == 'budget' and budget_form.is_valid():
        budget_form.save()
        messages.success(request, 'Monthly budget updated.')
        return redirect(f'{request.path}?month={selected_date:%Y-%m}')
    elif action == 'delete_expense':
        if not request.POST.get('expense_id'):
            raise Http404
        delete_expense = get_object_or_404(
            Expense,
            pk=request.POST.get('expense_id'),
            user=request.user,
        )
        delete_expense.delete()
        messages.success(request, 'Expense deleted.')
        return redirect(f'{request.path}?month={selected_date:%Y-%m}')

    expenses = Expense.objects.filter(
        user=request.user,
        date__year=selected_date.year,
        date__month=selected_date.month,
    )
    selected_category = request.GET.get('category', '')
    valid_categories = {value for value, _ in Expense.Category.choices}
    if selected_category in valid_categories:
        expenses = expenses.filter(category=selected_category)

    all_month_expenses = Expense.objects.filter(
        user=request.user,
        date__year=selected_date.year,
        date__month=selected_date.month,
    )
    total_spent = all_month_expenses.aggregate(total=Sum('amount'))['total'] or Decimal('0')
    month_expense_count = all_month_expenses.count()
    category_totals = dict(
        all_month_expenses.values('category')
        .annotate(total=Sum('amount'))
        .values_list('category', 'total')
    )
    maximum_category_total = max(category_totals.values(), default=Decimal('0'))
    category_breakdown = [
        {
            'value': value,
            'label': label,
            'total': category_totals.get(value, Decimal('0')),
            'percentage': (
                category_totals.get(value, Decimal('0')) * 100 / maximum_category_total
                if maximum_category_total else 0
            ),
        }
        for value, label in Expense.Category.choices
    ]

    return render(request, 'expensetracker/home.html', {
        'form': form,
        'picture_form': picture_form,
        'profile': profile,
        'expense_form': expense_form,
        'edit_form': edit_form,
        'budget_form': budget_form,
        'expenses': expenses,
        'month_expense_count': month_expense_count,
        'total_spent': total_spent,
        'monthly_budget': monthly_budget,
        'remaining_budget': monthly_budget.amount - total_spent,
        'category_breakdown': category_breakdown,
        'categories': Expense.Category.choices,
        'selected_category': selected_category,
        'selected_month': selected_date.strftime('%Y-%m'),
        'selected_month_label': selected_date.strftime('%B %Y'),
        'previous_month': previous_month_value,
        'next_month': next_month_value,
        'expense_modal_open': action == 'expense' and expense is not None and not edit_form.is_valid(),
        'profile_modal_open': action == 'profile' and (not form.is_valid() or not picture_form.is_valid()),
        'budget_modal_open': action == 'budget' and not budget_form.is_valid(),
    })


def register(request):
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return redirect('login')
    return render(request, 'expensetracker/register.html', {'form': form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect('login')