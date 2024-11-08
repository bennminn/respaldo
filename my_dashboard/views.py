import pandas as pd
import matplotlib.pyplot as plt
from django.shortcuts import render, redirect
from django.db import connection
from my_dashboard.forms import LoginForm
from django.contrib.auth import login, logout, authenticate
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from io import BytesIO
import base64
from django.http import JsonResponse
from django.contrib.auth.models import User
from .decorators import admin_only
from django.http import JsonResponse 
import json
from django.contrib.auth.decorators import login_required
from .utils import is_ajax, classify_face
from logs.models import Log
from django.core.files.base import ContentFile
from django.contrib.auth.models import User
from profiles.models import Profile

def generate_sales_growth_chart(df):
    # Agrupar por año y sumar las ventas
    sales_by_year = df.groupby(df['invoice_date'].dt.year)['quantity'].sum().reset_index()
    sales_by_year.columns = ['Year', 'Total Sales']

    # Calcular crecimiento año a año
    sales_by_year['Growth'] = sales_by_year['Total Sales'].pct_change() * 100  # Crecimiento en porcentaje

    # Crear gráfico
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(sales_by_year['Year'], sales_by_year['Total Sales'], marker='o', label='Ventas Totales', color='#489FB5')
    ax.set_xlabel('Año')
    ax.set_ylabel('Ventas Totales')
    ax.grid()
    plt.xticks(sales_by_year['Year'])
    
    # Guardar la imagen en un buffer
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    
    return base64.b64encode(image_png).decode('utf-8')

def calculate_total_sales(df):
    return df['quantity'].sum()

def calculate_retention_rate(df):
    purchase_counts = df['customer_id'].value_counts()
    total_customers = len(purchase_counts)
    retained_customers = (purchase_counts > 1).sum()
    retention_rate = (retained_customers / total_customers) * 100 if total_customers > 0 else 0
    return retention_rate

def generate_category_distribution_chart(df):
    fig, ax = plt.subplots(figsize=(10, 6))
    df.groupby('category')['quantity'].sum().plot(kind='bar', ax=ax, color='#489FB5', edgecolor='black')
    ax.set_xlabel('Categoría')
    ax.set_ylabel('Cantidad')
    plt.tight_layout()

    # Guardar la imagen en un buffer
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    
    return base64.b64encode(image_png).decode('utf-8')

@admin_only
def index(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT * FROM invoice;')
            invoices = cursor.fetchall()
        
        # Crear la lista de diccionarios para el DataFrame
        invoice_list = [{'category': row[1], 'quantity': row[2], 'customer_id': row[8], 'invoice_date': row[6]} for row in invoices]
        
        # Crear el DataFrame
        df_invoice = pd.DataFrame(invoice_list)
        
        df_invoice['invoice_date'] = pd.to_datetime(df_invoice['invoice_date'])
        
        if not df_invoice.empty:
            # Generar los gráficos
            category_chart = generate_category_distribution_chart(df_invoice)
            retention_rate = calculate_retention_rate(df_invoice)
            retention_rate = round(retention_rate, 4) 
            total_sales = calculate_total_sales(df_invoice)
            total_sales = "{:,}".format(total_sales)
            print(total_sales)
            sales_per_year = generate_sales_growth_chart(df_invoice)
            
            return render(request, 'index.html', {
                'category_chart': category_chart,
                'customer_chart': retention_rate,
                'total_sales': total_sales,
                'sales_per_year': sales_per_year
            })
    except:
        return render(request, 'index.html', {'error': 'No hay datos disponibles.'})

@csrf_exempt
def verify_user(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username')
        if User.objects.filter(username=username).exists():
            return JsonResponse({'found': True})
        else:
            return JsonResponse({'found': False})
    return JsonResponse({'found': False})

def login_succes(request):
    data = {"mesg": "", "form": LoginForm()}
    username = request.GET.get('username', '')
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid:
            username = request.POST.get("username")
            password = request.POST.get("password")
            user = authenticate(username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, "Inició sesión correctamente!!! :)")
                    return redirect(to='index')
                else:
                    data["mesg"] = "¡Nombre de usuario o contraseña no son correctos!"
            else:
                data["mesg"] = "¡Nombre de usuario o contraseña no son correctos!"
    return render(request, 'login.html', {'username': username})

def logout_succes(request):
    logout(request)
    messages.success(request, "Cerró sesión correctamente!!!")
    return redirect(to='login')

###########################################################

def get_username(request):
    if request.method == "GET":
        # Aquí puedes implementar la lógica para obtener el nombre de usuario
        username = "benja"  # Sustituir por lógica de obtención real
        user = User.objects.filter(username=username).first()
        if user:
            return JsonResponse({"username": user.username})
        return JsonResponse({"username": None})
    
# def scan(request):
#     return render(request, 'scan.html')

def login_view(request):
    return render(request, 'login.html', {})

def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def home_view(request):
    return render(request, 'index.html', {})

def find_user_view(request):
    if is_ajax(request):
        photo = request.POST.get('photo')
        _, str_img = photo.split(';base64')

        print(photo)
        decoded_file = base64.b64decode(str_img)
        print(decoded_file)

        x = Log()
        x.photo.save('upload.png', ContentFile(decoded_file))
        x.save()

        res = classify_face(x.photo.path)
        if res:
            user_exists = User.objects.filter(username=res).exists()
            if user_exists:
                user = User.objects.get(username=res)
                profile = Profile.objects.get(user=user)
                x.profile = profile
                x.save()

                login(request, user)
                return JsonResponse({'success': True})
        return JsonResponse({'success': False})











