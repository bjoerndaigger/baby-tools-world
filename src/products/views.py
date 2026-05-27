from django.contrib import messages
from django.db.models import Avg, Count
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm
from .models import Category, Comment, Product


def product_list(request: HttpRequest, category_slug: str | None = None) -> HttpResponse:
    """Display a list of products, optionally filtered by category."""
    categories = Category.objects.all()
    products = Product.objects.select_related("category").annotate(
        avg_rating=Avg("comments__rating"), total_ratings=Count("comments")
    )
    if category_slug:
        products = products.filter(category__slug=category_slug)
    return render(request, "products.html", {"categories": categories, "products": products})


def product_detail(request: HttpRequest, category_slug: str, pk: int) -> HttpResponse:
    """Display a product detail page and handle comment form submission."""
    product: Product = get_object_or_404(
        Product.objects.select_related("category").annotate(
            avg_rating=Avg("comments__rating"), total_ratings=Count("comments")
        ),
        pk=pk,
        category__slug=category_slug,
    )

    related_products = (
        Product.objects.filter(category=product.category)
        .exclude(pk=product.pk)
        .annotate(avg_rating=Avg("comments__rating"), total_ratings=Count("comments"))
        .order_by("-avg_rating", "-total_ratings", "name")[:8]
    )

    comments = product.comments.select_related("user").order_by("-created_at")

    if request.method == "POST":
        form = CommentForm(request.POST, initial={
                           "user": request.user if request.user.is_authenticated else None})
        if form.is_valid():
            rating: int = form.cleaned_data["rating"]
            text: str = form.cleaned_data.get("text", "")

            if request.user.is_authenticated:
                # Upsert: update existing comment or create a new one
                comment: Comment
                created: bool
                comment, created = Comment.objects.get_or_create(
                    product=product, user=request.user, defaults={
                        "rating": rating, "text": text}
                )
                if not created:
                    comment.rating = rating
                    comment.text = text
                    comment.save()
                messages.success(request, "Your rating was {}.".format(
                    "submitted" if created else "updated"))
            else:
                # Guest: create a new comment (no uniqueness constraint)
                comment = form.save(commit=False)
                comment.product = product
                comment.save()
                messages.success(request, "Thank you for your rating.")

            return redirect("product_detail", category_slug=category_slug, pk=product.pk)
    else:
        # Pre-fill form for authenticated user with existing comment (if any)
        initial: dict[str, object] = {}
        if request.user.is_authenticated:
            existing: Comment | None = product.comments.filter(user=request.user).first()
            if existing:
                initial = {"rating": existing.rating, "text": existing.text}
        form = CommentForm()

    return render(
        request,
        "product.html",
        {"product": product, "comments": comments,
            "related_products": related_products, "form": form},
    )
