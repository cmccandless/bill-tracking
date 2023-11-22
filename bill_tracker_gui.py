from datetime import date
from pathlib import Path

from tkinter import *
from tkinter import messagebox

# from tkinter import simpledialog
from tkinter import filedialog

# from tkinter import ttk

from bill_tracker import Ledger, parse_date, BudgetResults

COLUMN_WIDTH = 20

# TODO: parameterize
budget_file = Path("budget.yml")
last_pay_day = date(2023, 9, 15)
balance = 2564.6

check_recent = True


class Table:
    def __init__(self, parent, data):
        self.parent = parent
        self.data = data
        self.total_rows = len(data)
        self.total_columns = len(data[0])
        self.table_frame = Frame(parent)

    def pack(self):
        self.table_frame.pack()
        # code for creating table
        for i in range(self.total_rows):
            for j in range(self.total_columns):
                self.e = Entry(
                    self.table_frame, width=COLUMN_WIDTH, fg="blue", font=("Arial", 16, "bold")
                )

                self.e.grid(row=i, column=j)
                self.e.insert(END, self.data[i][j])


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

    def calculate_results(self):
        def paid_check_handler(
            bill_name: str, amount: float, check_days: int, messagebox_parent=self.results_frame
        ) -> bool:
            answer = messagebox.askyesno(
                title="TBD",
                message=f"Has {bill_name} (${amount:.2f}) been paid in the last {check_days} days?",
                parent=messagebox_parent,
            )
            if answer is None:
                raise ValueError("operation was cancelled")
            return answer

        if self.budget_file is None:
            raise ValueError("No budget file selected")

        ledger = Ledger(self.budget_file, check_handler=paid_check_handler)
        try:
            last_pay_day = parse_date(self.last_pay_day_entry.get())
        except ValueError:
            raise ValueError("Last Pay Day empty or invalid")
        try:
            balance = float(self.balance_entry.get())
        except ValueError:
            raise ValueError("Current balance is empty or invalid")
        return ledger.calculate(last_pay_day, balance, check_recent=check_recent)

    def display_allocations_table(self, results: BudgetResults):
        data = results.get_allocations(include_headers=True)
        table = Table(self.results_frame, data)
        table.pack()

    def display_summary(self, results: BudgetResults):
        summary_frame = Frame(self.results_frame)
        summary_frame.pack()

        rows = results.get_estimations()
        rows.extend(results.get_summary())
        rows.append(("Margin", results.margin))
        for row_index, (label, value) in enumerate(rows):
            Label(summary_frame, text=f"{label}: ").grid(column=0, row=row_index)
            Label(summary_frame, text=f"{value:.2f}").grid(column=1, row=row_index)

    def calculate(self):
        if self.results_frame is not None:
            self.results_frame.pack_forget()
        self.results_frame = Frame(self)
        self.results_frame.pack()
        scrollbar = Scrollbar(self.results_frame)
        scrollbar.pack(side=RIGHT, fill=Y)
        results = self.calculate_results()
        self.display_allocations_table(results)
        self.display_summary(results)

    def set_budget_file(self):
        answer = filedialog.askopenfilename(
            parent=self,
            initialdir=Path.cwd(),
            title="Select budget.yml",
            filetypes=[("YML files", ".yml .yaml"), ("all files", ".*")],
        )
        self.budget_file = Path(answer)
        self.budget_file_label.config(text=answer)

    def make_widgets(self):
        # don't assume that self.parent is a root window.
        # instead, call `winfo_toplevel to get the root window
        self.winfo_toplevel().title("Bill Tracker")

        controls_frame = Frame(self)
        controls_frame.pack()
        controls = []

        self.budget_file_label = Label(controls_frame, text="(none selected)")
        controls.append(
            (
                Label(controls_frame, text="budget.yml path:"),
                self.budget_file_label,
                Button(
                    controls_frame,
                    text="Select budget.yml",
                    command=self.set_budget_file,
                ),
            )
        )

        self.last_pay_day_entry = Entry(controls_frame)
        controls.append(
            (
                Label(controls_frame, text="Last Pay Day"),
                Label(controls_frame, text="(example: 2023/09/15)"),
                self.last_pay_day_entry,
            )
        )

        self.balance_entry = Entry(controls_frame)
        controls.append(
            (
                Label(controls_frame, text="Current Account Balance:"),
                Label(controls_frame, text="(example: 1234.56)"),
                self.balance_entry,
            )
        )

        controls.append(
            (None, Button(controls_frame, text="Calculate", command=self.calculate))
        )
        self.bind("<Return>", self.calculate)

        for row, control_group in enumerate(controls):
            for column, control in enumerate(control_group):
                if control is not None:
                    control.grid(column=column, row=row)


root = Tk()

app_width = 1920
app_height = 1000

screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

pos_x = (screen_width - app_width) // 2
pos_y = (screen_height - app_height) // 2

root.geometry(f"{app_width}x{app_height}+{pos_x}+{pos_y}")
root.resizable(True, True)

main_frame = MainFrame(root)
root.mainloop()
