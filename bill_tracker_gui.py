from datetime import date
from pathlib import Path

from tkinter import *
from tkinter import messagebox
from tkinter import simpledialog
from tkinter import filedialog
# from tkinter import ttk

from bill_tracker import Ledger, parse_date

# TODO: parameterize
budget_file = Path("budget.yml")
last_pay_day = date(2023,9,15)
balance = 2564.6

check_recent = True



class Table:
    def __init__(self,root,data):
        total_rows = len(data)
        total_columns = len(data[0])
        # code for creating table
        for i in range(total_rows):
            for j in range(total_columns):
                 
                self.e = Entry(
                    root,
                    width=20,
                    fg='blue',
                    font=('Arial',16,'bold')
                )
                 
                self.e.grid(row=i, column=j)
                self.e.insert(END, data[i][j])

class MainFrame(Frame):
    def __init__(self, parent=None):
        Frame.__init__(self, parent)
        self.parent = parent
        self.results_frame = None
        self.budget_file = None
        self.budget_file_label = None
        # self.last_pay_day = None
        # self.balance = None
        self.pack()
        self.make_widgets()

        Tk.report_callback_exception = self.report_callback_exception

    def report_callback_exception(self, exc, val, tb):
        messagebox.showerror("Error", message=str(val))
        
    def calculate(self):
        if self.results_frame is not None:
            self.results_frame.pack_forget()
        self.results_frame = Frame(self)
        self.results_frame.pack()
        def paid_check_handler(bill_name: str, check_days: int, messagebox_parent=self.results_frame) -> bool:
            answer = messagebox.askyesno(
                title="TBD",
                message=f"Has {bill_name} been paid in the last {check_days} days?",
                parent=messagebox_parent,
                
            )
            if answer is None:
                raise ValueError("operation was cancelled")
            return answer
        
        if self.budget_file is None:
            raise ValueError("No budget file selected")

        ledger = Ledger(
            self.budget_file,
            check_handler=paid_check_handler
        )
        try:
            last_pay_day = parse_date(self.last_pay_day_entry.get())
        except ValueError:
            raise ValueError("Last Pay Day empty or invalid")
        try:
            balance = float(self.balance_entry.get())
        except ValueError:
            raise ValueError("Current balance is empty or invalid")
        results = ledger.calculate(
            last_pay_day,
            balance,
            check_recent=check_recent
        )

        data = results.get_allocations(include_headers=True)
        table = Table(self.results_frame, data)

    def set_budget_file(self):
        answer = filedialog.askopenfilename(
            parent=self,
            initialdir=Path.cwd(),
            title="Select budget.yml",
            filetypes=[('YML files', '.yml .yaml'), ('all files', '.*')],
        )
        self.budget_file = Path(answer)
        self.budget_file_label.config(text=answer)

    def make_widgets(self):
        # don't assume that self.parent is a root window.
        # instead, call `winfo_toplevel to get the root window
        self.winfo_toplevel().title("Bill Tracker")

        Label(self, text="budget.yml path:").pack()
        self.budget_file_label = Label(self, text="")
        self.budget_file_label.pack()
        Button(self, text="Select budget.yml", command=self.set_budget_file).pack()

        Label(self, text="Last Pay Day").pack()
        self.last_pay_day_entry = Entry(self)
        self.last_pay_day_entry.pack()

        Label(self, text="Current Account Balance:").pack()
        self.balance_entry = Entry(self)
        self.balance_entry.pack()
        # answer = simpledialog.askstring(
        #     title="Last Pay Day",
        #     prompt="(example: 2023/09/15)",
        #     initialvalue="YYYY/MM/DD",
        # )
        # self.last_pay_day = parse_date(answer)

        # self.balance = simpledialog.askfloat(
        #     title="Current Balance",
        #     prompt="example: 1234.56",
        # )

        calc_button = Button(self, text="Calculate", command=self.calculate)
        calc_button.pack()


root = Tk()

app_width = 1000
app_height = 1000

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

pos_x = (screen_width - app_width) // 2
pos_y = (screen_height - app_height) // 2

root.geometry(f"{app_width}x{app_height}+{pos_x}+{pos_y}")

main_frame = MainFrame(root)
# main_frame.attributes("-topmost", 1)
root.mainloop()
