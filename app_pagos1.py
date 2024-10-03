import sqlite3
import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.checkbox import CheckBox
from kivy.uix.spinner import Spinner
from kivy.uix.filechooser import FileChooserIconView
import os
import csv

ITEMS = [
    'Acce', 'PC', 'PS4', 'Cartucho CANON', 'Cheq', 'Tin', 'Cop', 'HV', 
    'Del', 'Eng', 'Esc', 'Eset', 'Factura', 'Fig', 'Imp', 'Foto', 'Imp PE', 
    'Office', 'Plas', 'RP', 'FF', 'Reda', 'Scan', 'Tarjeta', 'Técnico', 
    'Var', 'Netflix'
]

# Conexión a la base de datos SQLite
conn = sqlite3.connect('payments.db')
c = conn.cursor()

# Crear la tabla si no existe
c.execute('''
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_name TEXT,
        banca_name TEXT,
        items TEXT,
        total REAL,
        payment_type TEXT,
        is_invoiced TEXT,
        time_added TEXT
    )
''')
conn.commit()

class AddPaymentPopup(Popup):
    def __init__(self, add_payment_callback, **kwargs):
        super().__init__(**kwargs)
        self.add_payment_callback = add_payment_callback
        self.title = "Agregar Nuevo Pago"
        self.size_hint = (0.9, 0.8)

        self.layout = BoxLayout(orientation='vertical')
        
        self.client_name_input = TextInput(hint_text='Nombre del Cliente (Opcional)')
        self.banca_name_input = TextInput(hint_text='Nombre de Quien Hace el Pago (Opcional)', disabled=True)
        
        self.items_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.items_layout.bind(minimum_height=self.items_layout.setter('height'))
        self.add_item_row()

        self.add_more_items_button = Button(text="Agregar otro ítem", on_press=self.add_item_row)
        
        self.payment_type_spinner = Spinner(
            text='Selecciona el Tipo de Pago',
            values=('Efectivo', 'Banca'),
            size_hint=(1, 0.3)
        )
        self.payment_type_spinner.bind(text=self.on_payment_type_change)

        self.is_invoiced_label = Label(text="¿Facturado?", size_hint=(1, 0.2))
        self.is_invoiced_checkbox = CheckBox(size_hint=(1, 0.2))

        add_button = Button(text='Agregar Pago', on_press=self.add_payment)

        self.layout.add_widget(self.client_name_input)
        self.layout.add_widget(self.banca_name_input)
        self.layout.add_widget(self.items_layout)
        self.layout.add_widget(self.add_more_items_button)
        self.layout.add_widget(self.payment_type_spinner)
        self.layout.add_widget(self.is_invoiced_label)
        self.layout.add_widget(self.is_invoiced_checkbox)
        self.layout.add_widget(add_button)

        self.content = self.layout

    def on_payment_type_change(self, spinner, text):
        # Habilitar campo de nombre de quien hace la banca si el tipo es 'Banca'
        if text == 'Banca':
            self.banca_name_input.disabled = False
        else:
            self.banca_name_input.disabled = True
            self.banca_name_input.text = ''

    def add_item_row(self, instance=None):
        item_row = BoxLayout(size_hint_y=None, height=40)
        item_spinner = Spinner(
            text='Selecciona un ítem',
            values=ITEMS,
            size_hint=(0.4, 1)
        )
        amount_input = TextInput(hint_text='Monto', input_filter='float', size_hint=(0.3, 1))
        details_input = TextInput(hint_text='Detalles (Opcional)', size_hint=(0.3, 1))
        item_row.add_widget(item_spinner)
        item_row.add_widget(amount_input)
        item_row.add_widget(details_input)
        self.items_layout.add_widget(item_row)

    def add_payment(self, instance):
        name = self.client_name_input.text
        banca_name = self.banca_name_input.text
        payment_type = self.payment_type_spinner.text
        is_invoiced = "Sí" if self.is_invoiced_checkbox.active else "No"
        time_added = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        items = []
        total_amount = 0
        for item_row in self.items_layout.children:
            item_spinner = item_row.children[2]
            amount_input = item_row.children[1]
            details_input = item_row.children[0]
            item = item_spinner.text
            amount = amount_input.text
            details = details_input.text or "N/A"
            if item and amount:
                items.append((item, float(amount), details))
                total_amount += float(amount)

        if items:
            self.add_payment_callback(name, banca_name, items, total_amount, payment_type, is_invoiced, time_added)
            self.dismiss()

class PaymentApp(App):
    def build(self):
        self.payments = []  # Almacena temporalmente los pagos antes de guardarlos
        
        # Configuración de la interfaz principal
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        self.payment_list_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.payment_list_layout.bind(minimum_height=self.payment_list_layout.setter('height'))

        scroll_view = ScrollView(size_hint=(1, 0.8))
        scroll_view.add_widget(self.payment_list_layout)

        add_payment_button = Button(text='Agregar Nuevo Pago', size_hint=(1, 0.1), on_press=self.open_add_payment_popup)
        summary_button = Button(text="Generar Resumen del Día", size_hint=(1, 0.1))
        summary_button.bind(on_press=self.ask_group_items)  # Preguntar antes de generar resumen

        layout.add_widget(scroll_view)
        layout.add_widget(add_payment_button)
        layout.add_widget(summary_button)

        return layout

    def open_add_payment_popup(self, instance):
        popup = AddPaymentPopup(self.add_payment)
        popup.open()

    def add_payment(self, name, banca_name, items, total_amount, payment_type, is_invoiced, time_added):
        payment_str = f"Cliente: {name or 'Desconocido'}, Tipo: {payment_type}, Facturado: {is_invoiced}, Hora: {time_added}, Total: {total_amount:.2f}\n"
        if payment_type == 'Banca' and banca_name:
            payment_str += f"  Quien Hace el Pago: {banca_name}\n"
        for item, amount, details in items:
            payment_str += f"  Ítem: {item}, Monto: {amount:.2f}, Detalles: {details}\n"

        # Guardar el pago en la base de datos
        c.execute('''
            INSERT INTO payments (client_name, banca_name, items, total, payment_type, is_invoiced, time_added)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, banca_name, str(items), total_amount, payment_type, is_invoiced, time_added))
        conn.commit()

        self.payments.append((items, total_amount, is_invoiced))

        payment_label = Label(text=payment_str, size_hint_y=None, height=40 + len(items) * 20)
        self.payment_list_layout.add_widget(payment_label)
    
    def ask_group_items(self, instance):
        # Crear popup para preguntar sobre la agrupación de ítems
        group_popup_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        group_label = Label(text="¿Desea agrupar los ítems?")
        group_popup_layout.add_widget(group_label)
        
        # Crear checkbox para decidir si agrupar o no
        group_choice = CheckBox()
        group_popup_layout.add_widget(group_choice)
        
        # Botón para confirmar la elección
        confirm_button = Button(text="Confirmar", size_hint=(1, 0.2))  
        
        # Pasar la elección a la función generate_daily_summary
        confirm_button.bind(on_press=lambda x: self.generate_daily_summary(group_choice.active))
        group_popup_layout.add_widget(confirm_button)
        
        # Crear el popup
        self.group_popup = Popup(title="Agrupar Ítems", content=group_popup_layout, size_hint=(0.6, 0.4))
        self.group_popup.open()

    def generate_daily_summary(self, group_items):
        # Cerrar el popup
        self.group_popup.dismiss()
        
        # Obtener productos vendidos desde la base de datos
        c.execute('SELECT items, total FROM payments')
        productos_vendidos = c.fetchall()
        
        # Crear el texto del resumen del día con base
