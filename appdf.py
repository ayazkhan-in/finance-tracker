import datetime
import os
import sqlite3
import tkinter as tk
from tkinter import messagebox as mb, ttk, Frame, Label, Button, Entry, OptionMenu, StringVar, DoubleVar, END, BOTH, X, W, E, GROOVE, Toplevel
from tkinter.filedialog import asksaveasfilename
from tkcalendar import DateEntry
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk


root_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(root_dir, 'ExpenseTracker.db')

dbconnector = None
cursor = None

try:
    dbconnector = sqlite3.connect(db_path)
    cursor = dbconnector.cursor()

    cursor.execute('''CREATE TABLE IF NOT EXISTS ExpenseTracker (
                       ID INTEGER PRIMARY KEY AUTOINCREMENT,
                       Date TEXT NOT NULL,
                       Payee TEXT NOT NULL,
                       Description TEXT NOT NULL,
                       Amount REAL NOT NULL,
                       ModeOfPayment TEXT NOT NULL,
                       Category TEXT NOT NULL
                   )''')
    dbconnector.commit()

except sqlite3.Error as e:
    mb.showerror("Database Error", f"Could not connect to or create database:\n{e}\n\nThe application will close.")
    exit()


def listAllExpenses():
    if not dbconnector: return
    try:
        for item in data_table.get_children():
            data_table.delete(item)

        cursor.execute('SELECT * FROM ExpenseTracker ORDER BY Date DESC, ID DESC')
        data = cursor.fetchall()
        for val in data:
            data_table.insert('', END, values=val)
    except sqlite3.Error as e:
        mb.showerror("Database Error", f"Could not fetch expenses: {e}")


def clearFields():
    todayDate = datetime.date.today()
    description.set('')
    payee.set('')
    amount.set(0.0)
    if paymentOptions:
        modeOfPayment.set(paymentOptions[0])
    if categoryOptions:
        category.set(categoryOptions[0])
    dateField.set_date(todayDate)
    if data_table.selection():
        data_table.selection_remove(data_table.selection())

def addAnotherExpense():
    if not dbconnector: return

    if not dateField.get() or not payee.get() or not description.get() or not modeOfPayment.get() or not category.get():
        mb.showerror('Fields empty!', "Please fill all the missing fields.")
        return

    try:
        amount_val = float(amount.get())
        if amount_val <= 0:
            mb.showerror('Invalid Amount', 'Amount must be a positive number.')
            return
    except ValueError:
        mb.showerror('Invalid Amount', 'Please enter a valid number for the amount.')
        return

    try:
        cursor.execute(
            'INSERT INTO ExpenseTracker (Date, Payee, Description, Amount, ModeOfPayment, Category) VALUES (?, ?, ?, ?, ?, ?)',
            (dateField.get(), payee.get(), description.get(), amount_val, modeOfPayment.get(), category.get())
        )
        dbconnector.commit()
        clearFields()
        listAllExpenses()
        mb.showinfo('Expense added', 'The expense has been added.')
    except sqlite3.Error as e:
        mb.showerror('Database Error', f'Could not add expense: {e}')


def removeExpense():
    if not dbconnector: return

    selected_items = data_table.selection()
    if not selected_items:
        mb.showerror('No record selected!', 'Please select a record from the table to delete!')
        return

    current_item_id = selected_items[0]
    currentSelectedExpense = data_table.item(current_item_id)
    valuesSelected = currentSelectedExpense['values']

    if not valuesSelected:
        mb.showerror('Error', 'Could not retrieve expense details for deletion.')
        return

    expense_id = valuesSelected[0]
    confirm_desc = valuesSelected[3] if len(valuesSelected) > 3 else f"ID: {expense_id}"

    confirmation = mb.askyesno('Confirm Deletion',
                               f'Are you sure you want to delete the record for:\n"{confirm_desc}" (ID: {expense_id})?')

    if confirmation:
        try:
            cursor.execute('DELETE FROM ExpenseTracker WHERE ID = ?', (expense_id,))
            dbconnector.commit()
            listAllExpenses()
            clearFields()
            mb.showinfo('Record deleted', 'The selected expense has been deleted.')
        except sqlite3.Error as e:
            mb.showerror('Database Error', f'Could not delete expense: {e}')

def exportToPdf():
    if not dbconnector: return

    file_path = asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        title="Save Expenses as PDF"
    )

    if not file_path:
        return

    try:
        cursor.execute('SELECT Date, Payee, Description, Amount, ModeOfPayment, Category FROM ExpenseTracker ORDER BY Date DESC, ID DESC')
        data = cursor.fetchall()

        if not data:
            mb.showinfo("Export", "No expense data found to export.")
            return

        doc = SimpleDocTemplate(file_path, pagesize=letter)
        story = []

        headers = ['Date', 'Payee', 'Description', 'Amount', 'Payment Mode', 'Category']
        table_data = [headers] + list(data)

        table = Table(table_data)

        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
             ('ALIGN', (3, 0), (3, -1), 'RIGHT'), # Align Amount column to the right
        ])

        table.setStyle(style)

        # Attempt to set column widths dynamically or fixed
        col_widths = [doc.width * 0.12, doc.width * 0.15, doc.width * 0.25, doc.width * 0.10, doc.width * 0.18, doc.width * 0.18]
        table.widths = col_widths


        story.append(table)
        doc.build(story)

        mb.showinfo("Export Successful", f"Expenses exported to {file_path}")

    except Exception as e:
        mb.showerror("Export Error", f"Could not export expenses to PDF:\n{e}")


def showVisualization():
    if not dbconnector: return

    try:
        cursor.execute('SELECT Category, SUM(Amount) FROM ExpenseTracker GROUP BY Category HAVING SUM(Amount) > 0')
        data = cursor.fetchall()

        if not data:
            mb.showinfo("Visualization", "No expense data found to visualize.")
            return

        categories = [row[0] for row in data]
        amounts = [row[1] for row in data]

        viz_window = Toplevel(mainWindow)
        viz_window.title("Expense Summary by Category")
        viz_window.geometry("800x600")

        fig, ax = plt.subplots(figsize=(8, 6))
        ax.pie(amounts, labels=categories, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        ax.set_title('Expense Distribution by Category')

        canvas = FigureCanvasTkAgg(fig, master=viz_window)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=BOTH, expand=True)

        toolbar = NavigationToolbar2Tk(canvas, viz_window)
        toolbar.update()
        canvas.get_tk_widget().pack(side=tk.TOP, fill=BOTH, expand=True)

    except Exception as e:
        mb.showerror("Visualization Error", f"Could not generate visualization:\n{e}")


def on_closing():
    if mb.askokcancel("Quit", "Do you want to quit the Expense Tracker?"):
        if dbconnector:
            dbconnector.close()
        mainWindow.destroy()


mainWindow = tk.Tk()
mainWindow.title("Simple Expense Tracker")
mainWindow.geometry("1000x600")
mainWindow.configure(bg="#F5F5F5")

style = ttk.Style()
style.configure('TButton', font=('Bahnschrift Condensed', 12), padding=5)
style.configure('TLabel', font=('Bahnschrift Condensed', 12), background="#F5F5F5")
style.configure('Treeview.Heading', font=('Bahnschrift Condensed', 13, 'bold'), background='#AED6F1', foreground='#1B4F72')
style.configure('Treeview', font=('Arial', 11), rowheight=25)
style.map('Treeview', background=[('selected', '#3498DB')])

titleLabel = Label(mainWindow, text="Simple Expense Tracker", font=("Bahnschrift Condensed", 20, "bold"), bg="#5DADE2", fg="#FFFFFF", pady=10)
titleLabel.pack(fill=X)

contentFrame = Frame(mainWindow, bg="#FFFFFF")
contentFrame.pack(fill=BOTH, expand=True, padx=10, pady=10)

tableFrame = Frame(contentFrame)
tableFrame.pack(side=tk.LEFT, fill=BOTH, expand=True, padx=(0, 10))

treeScrollY = ttk.Scrollbar(tableFrame)
treeScrollY.pack(side=tk.RIGHT, fill=tk.Y)
treeScrollX = ttk.Scrollbar(tableFrame, orient=tk.HORIZONTAL)
treeScrollX.pack(side=tk.BOTTOM, fill=tk.X)

data_table = ttk.Treeview(
    tableFrame,
    columns=('ID', 'Date', 'Payee', 'Description', 'Amount', 'ModeOfPayment', 'Category'),
    show='headings',
    style='Treeview',
    yscrollcommand=treeScrollY.set,
    xscrollcommand=treeScrollX.set
)
treeScrollY.config(command=data_table.yview)
treeScrollX.config(command=data_table.xview)

data_table.heading('ID', text='ID')
data_table.column('ID', width=40, anchor=tk.CENTER)
data_table.heading('Date', text='Date')
data_table.column('Date', width=100, anchor=tk.CENTER)
data_table.heading('Payee', text='Payee')
data_table.column('Payee', width=150)
data_table.heading('Description', text='Description')
data_table.column('Description', width=250)
data_table.heading('Amount', text='Amount')
data_table.column('Amount', width=100, anchor=tk.E)
data_table.heading('ModeOfPayment', text='Payment Mode')
data_table.column('ModeOfPayment', width=120)
data_table.heading('Category', text='Category')
data_table.column('Category', width=120)

data_table.pack(fill=BOTH, expand=True)


controlsFrame = Frame(contentFrame, bg="#F5F5F5", width=300)
controlsFrame.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0))
controlsFrame.pack_propagate(False)

inputFrame = Frame(controlsFrame, padx=10, pady=10, bg="#F5F5F5")
inputFrame.pack(pady=(10, 10), fill=X)

Label(inputFrame, text="Date:", font=("Bahnschrift Condensed", "12"), bg="#F5F5F5").grid(row=0, column=0, sticky=tk.W, pady=5)
dateField = DateEntry(inputFrame, width=18, date_pattern='y-mm-dd', background='#E1F5FE', foreground='black', borderwidth=2, font=("Arial", 11))
dateField.grid(row=0, column=1, sticky=tk.W+tk.E, padx=10, pady=5)

Label(inputFrame, text="Payee:", font=("Bahnschrift Condensed", "12"), bg="#F5F5F5").grid(row=1, column=0, sticky=tk.W, pady=5)
payee = StringVar()
Entry(inputFrame, textvariable=payee, font=("Arial", 11), width=20).grid(row=1, column=1, sticky=tk.W+tk.E, padx=10, pady=5)

Label(inputFrame, text="Description:", font=("Bahnschrift Condensed", "12"), bg="#F5F5F5").grid(row=2, column=0, sticky=tk.W, pady=5)
description = StringVar()
Entry(inputFrame, textvariable=description, font=("Arial", 11), width=20).grid(row=2, column=1, sticky=tk.W+tk.E, padx=10, pady=5)

Label(inputFrame, text="Amount:", font=("Bahnschrift Condensed", "12"), bg="#F5F5F5").grid(row=3, column=0, sticky=tk.W, pady=5)
amount = DoubleVar(value=0.0)
Entry(inputFrame, textvariable=amount, font=("Arial", 11), width=20).grid(row=3, column=1, sticky=tk.W+tk.E, padx=10, pady=5)

Label(inputFrame, text="Payment Mode:", font=("Bahnschrift Condensed", "12"), bg="#F5F5F5").grid(row=4, column=0, sticky=tk.W, pady=5)
modeOfPayment = StringVar()
paymentOptions = ['Cash', 'Credit Card', 'Debit Card', 'Net Banking', 'UPI', 'Others']
if paymentOptions: modeOfPayment.set(paymentOptions[0])
payment_menu = OptionMenu(inputFrame, modeOfPayment, *paymentOptions)
payment_menu.grid(row=4, column=1, sticky=tk.W+tk.E, padx=10, pady=5)
payment_menu.config(font=("Arial", 10))

Label(inputFrame, text="Category:", font=("Bahnschrift Condensed", "12"), bg="#F5F5F5").grid(row=5, column=0, sticky=tk.W, pady=5)
category = StringVar()
categoryOptions = ['Food', 'Groceries', 'Bills', 'Transportation', 'Entertainment', 'Shopping', 'Housing', 'Health', 'Education', 'Others']
if categoryOptions: category.set(categoryOptions[0])
category_menu = OptionMenu(inputFrame, category, *categoryOptions)
category_menu.grid(row=5, column=1, sticky=tk.W+tk.E, padx=10, pady=5)
category_menu.config(font=("Arial", 10))

inputFrame.columnconfigure(1, weight=1)

actionFrame = Frame(controlsFrame, padx=10, pady=10, bg="#F5F5F5")
actionFrame.pack(pady=(10,10), fill=X)

btn_pady = 8

Button(actionFrame, text="Add Expense", font=("Bahnschrift Condensed", "12"), relief=GROOVE,
       bg="#58D68D", fg="white", activebackground="#2ECC71", command=addAnotherExpense).pack(fill=X, pady=btn_pady)

Button(actionFrame, text="Clear Fields", font=("Bahnschrift Condensed", "12"), relief=GROOVE,
       bg="#FAD7A0", fg="#6E2C00", activebackground="#F5B041", command=clearFields).pack(fill=X, pady=btn_pady)

Button(actionFrame, text="Delete Selected", font=("Bahnschrift Condensed", "12"), relief=GROOVE,
       bg="#EC7063", fg="white", activebackground="#E74C3C", command=removeExpense).pack(fill=X, pady=btn_pady)

Button(actionFrame, text="Export to PDF", font=("Bahnschrift Condensed", "12"), relief=GROOVE,
       bg="#5DADE2", fg="white", activebackground="#3498DB", command=exportToPdf).pack(fill=X, pady=btn_pady)

Button(actionFrame, text="View Summary", font=("Bahnschrift Condensed", "12"), relief=GROOVE,
       bg="#AF7AC5", fg="white", activebackground="#9B59B6", command=showVisualization).pack(fill=X, pady=btn_pady)


exitButton = Button(controlsFrame, text="Exit Application", font=("Bahnschrift Condensed", "13"), relief=GROOVE,
                    bg="#ABB2B9", fg="#212F3C", activebackground="#85929E", command=on_closing)
exitButton.pack(side=tk.BOTTOM, fill=X, padx=10, pady=(20, 10))


if dbconnector:
    listAllExpenses()
    dateField.focus_set()

mainWindow.protocol("WM_DELETE_WINDOW", on_closing)
mainWindow.mainloop()