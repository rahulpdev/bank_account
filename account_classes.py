import datetime
import setup_db as ldb

# Connect to local MySql server
my_local_db = ldb.initialise_local_db_connection('bank')


class Bank:
    def __init__(self, name, parent=None):
        self.name = name
        self.parent = parent
        self.account_types = {'Current Account', 'Savings Account', 'Business Account'}
        self.branches = []

    def __repr__(self):
        return "{}('{}','{}')".format(
            __class__.__name__, self.name, self.parent
        )

    def __str__(self):
        return self.name

    def __eq__(self, other):
        if not isinstance(other, Bank):
            return NotImplemented
        return self.name == other.name

    def add_branch(self, new_branch):
        if new_branch not in self.branches:
            new_branch.bank = self
            self.branches.append(new_branch)


class Branch:
    def __init__(self, address_one, sort_code):
        self.address_one = address_one
        self.sort_code = sort_code
        self.customers = []
        self.bank = None

    def __repr__(self):
        return "{}('{}','{}')".format(
            __class__.__name__, self.address_one, self.sort_code
        )

    def __str__(self):
        return str(self.address_one)

    def __eq__(self, other):
        if not isinstance(other, Branch):
            return NotImplemented
        return self.sort_code == other.sort_code

    def add_customer(self, new_customer):
        if new_customer not in self.customers:
            new_customer.branch = self
            new_customer.accounts = {
                item: [] for item in self.bank.account_types
            }
            self.customers.append(new_customer)


class Customer:
    def __init__(self, first_name, last_name, overdraft=None):
        self.first_name = first_name
        self.last_name = last_name
        self.overdraft = overdraft
        self.branch = None
        self.accounts = {}
        self.cards = []

    def __repr__(self):
        return "{}('{}','{}')".format(
            __class__.__name__, self.first_name, self.last_name
        )

    def __str__(self):
        return self.first_name + " " + self.last_name

# Customer object not defined with d.o.b. or address hence limited equality condition
    def __eq__(self, other):
        if not isinstance(other, Customer):
            return NotImplemented
        return self.first_name == other.first_name and self.last_name == other.last_name

    def add_account(self, new_account, account_type):
        if account_type not in self.accounts.keys():
            self.accounts[account_type] = []
        if new_account not in self.accounts[account_type]:
            new_account.holder.append(self)
            self.accounts[account_type].append(new_account)

    def add_card(self, new_card):
        if new_card not in self.cards:
            new_card.holder = self
            self.cards.append(new_card)

    def balance(self):
        total = 0
        for account_type in self.accounts:
            for account in account_type:
                total += account.balance
        return total


# Parent class for general bank account with no interest, no fees, no overdraft and no cap on number of debits.
class Account:
    interest = 0.0
    overdrawn_fee = None
    maintenance_fee_period = 1
    maintenance_fee = None
    transaction_fee = None
    debit_cap = None
    waive_atm_fee = False

    def __init__(self, number, currency='gbp', overdraft=None):
        self.number = number
        self.currency = currency
        self.overdraft = overdraft
        self.transaction_history = {
            'credit': [],
            'debit': []
        }
        self.is_frozen = False
        self.holder = []

    def __repr__(self):
        return "{}({},'{}',{})".format(
            __class__.__name__, self.number, self.currency, self.overdraft
        )

    def __str__(self):
        return self.number

    def __eq__(self, other):
        if not isinstance(other, Account):
            return NotImplemented
        return self.number == other.number

    # Add a new joint account holder to the existing account
    def add_joint_holder(self, new_holder):
        if new_holder not in self.holder:
            self.holder.append(new_holder)

    # return transactions in reverse chronological order
    def return_transaction(self, max_num):
        transactions = ldb.sql_query_fetchall(my_local_db, f"SELECT * FROM transactions WHERE account_id = {self.number}")
        return sorted(transactions, key=lambda item: item[5], reverse=True)[:max_num]

    # Add a new transaction to the transactions table
    def add_transaction(self, amount, trans_type, category, description=None):
        my_sql_query = "INSERT INTO transactions (account_id, amount, type, category, description, date_time) VALUES (%s, %s, %s, %s, %s, %s)"
        ldb.sql_query_commit(my_local_db, my_sql_query, (self.number, amount, trans_type, category, description, datetime.datetime.utcnow()))
        if trans_type == 'debit':
            # Add a new transaction for any transaction fees
            if self.transaction_fee is not None:
                ldb.sql_query_commit(my_local_db, my_sql_query, (self.number, self.transaction_fee, trans_type, 'fee', 'transaction fee', datetime.datetime.utcnow()))
            # Add a new transaction for an ATM fee refund if applicable
            if self.waive_atm_fee is True and description == 'atm fee':
                ldb.sql_query_commit(my_local_db, my_sql_query, (self.number, amount, 'credit', 'cr', 'refund atm fee', datetime.datetime.utcnow()))
            if self.balance() < 0.0 - float(self.overdraft):
                # Add a new transaction for an overdraft fee
                if self.overdrawn_fee is not None:
                    ldb.sql_query_commit(my_local_db, my_sql_query, (self.number, self.overdrawn_fee, trans_type, 'fee', 'account overdrawn fee', datetime.datetime.utcnow()))
                else:
                    # Add a new transaction to offset the debit transaction if the account has overdraft protection
                    # Code assumes Accounts with None overdrawn fee also waive atm fee
                    trans_type = 'credit'
                    ldb.sql_query_commit(my_local_db, my_sql_query, (self.number, amount, trans_type, 'ref', 'unpaid item', datetime.datetime.utcnow()))
                    if self.transaction_fee is not None:
                        ldb.sql_query_commit(my_local_db, my_sql_query, (self.number, self.transaction_fee, trans_type, 'ref', 'unpaid item', datetime.datetime.utcnow()))
                    return False
        return True

    def balance(self):
        total = 0.0
        transactions = ldb.sql_query_fetchall(my_local_db, f"SELECT amount, type FROM transactions WHERE account_id = {self.number}")
        for transaction in transactions:
            if transaction[1] == 'credit':
                total += float(transaction[0])
            else:
                total -= float(transaction[0])
        return total


# Parent class for general card with default pin and no link to a bank account
class Card:
    def __init__(self, number, pin, expiry_date=datetime.date.today()+datetime.timedelta(days=365*3)):
        self.number = number
        self.transaction_networks = {'link'}
        self.expiry_date = expiry_date
        self.holder = None
        self.account = None
        self.pin = pin

    def __repr__(self):
        return "{}('{}', '{}')".format(
            __class__.__name__, self.number, self.pin
        )

    def __str__(self):
        return self.number

    def __eq__(self, other):
        if not isinstance(other, Card):
            return NotImplemented
        return self.number == other.number and self.expiry_date == other.expiry_date and self.holder == other.holder

    def set_pin(self, new_pin):
        my_sql_query = "UPDATE cards SET pin = (%s) WHERE number = (%s) AND holder_firstname = (%s) AND holder_lastname = (%s)"
        if len(new_pin) == 4 and new_pin.isnumeric():
            ldb.sql_query_commit(my_local_db, my_sql_query, (new_pin, self.number, self.holder.first_name, self.holder.last_name))

    def link_account(self, new_account):
        my_sql_query = "UPDATE cards SET linked_account = (%s) WHERE number = (%s) AND holder_firstname = (%s) AND holder_lastname = (%s)"
        ldb.sql_query_commit(my_local_db, my_sql_query, (new_account.number, self.number, self.holder.first_name, self.holder.last_name))


class CurrentAccount(Account):
    interest = 0.01
    overdrawn_fee = 15.0
    maintenance_fee = 5.0

    def __init__(self, number, currency='gbp', overdraft=250.0):
        super().__init__(number, currency, overdraft)


class SavingsAccount(Account):
    interest = 0.04
    debit_cap = 5
    waive_atm_fee = True

    def __init__(self, number, currency='gbp', overdraft=0.0):
        super().__init__(number, currency, overdraft)


class BusinessAccount(Account):
    overdrawn_fee = 40.0
    maintenance_fee = 10.0
    transaction_fee = 1.5

    def __init__(self, number, currency='gbp', overdraft=1000.0):
        super().__init__(number, currency, overdraft)


# Transaction class for debit or credit that stores amounts as float
class Transaction:
    def __init__(self, amount, transaction_type, category, description=None):
        self.amount = float(amount)
        self.transaction_type = transaction_type
        self.category = category
        self.description = description
        self.date_time = datetime.datetime.utcnow()
        self.account = None

    def __repr__(self):
        return "{}({},'{}','{}','{}')".format(
            __class__.__name__, self.amount, self.transaction_type, self.category, self.description
        )

    def __str__(self):
        return str(self.amount)

    def __float__(self):
        return self.amount

    def __eq__(self, other):
        if not isinstance(other, Transaction):
            return NotImplemented
        return self.account == other.account and self.transaction_type == other.transaction_type and self.date_time == other.date_time
