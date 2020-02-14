import setup_db as ldb
import account_classes as acc

'''
ATM with credits, debits, transfers, combined balances display and latest transactions display.
Change card pin and change card linked account features exist.
Customers have current, savings and business accounts with overdrafts and overdraft fees.
Business accounts have debit transaction fees, savings accounts have overdraft protection.

Implement overall overdraft feature
Implement debit cap feature
v2.0 Fix issue with transfers
'''


# General ATM class with 0-9 key pad entry, 4 screens, 5 activity types and 4 withdrawal amounts
class Atm:
    atm_fee = None

    def __init__(self, address):
        self.address = address
        self.transaction_networks = {'link'}
        self.account_types_screen = {
            '5': 'Change card PIN',
            '6': 'Display Balance',
            '7': 'End'
        }
        self.accounts_screen = {
            '6': 'Display Balance',
            '7': 'Back'
        }
        self.activity_screen = {
            '1': 'Debit',
            '2': 'Credit',
            '3': 'Transfer',
            '4': 'Link account to card',
            '5': 'Print 10 Transactions',
            '6': 'Display Balance',
            '7': 'Back'
        }
        self.withdraw_screen = {
            '1': '10',
            '2': '20',
            '3': '50',
            '4': '100',
            '7': 'Back'
        }

    def __repr__(self):
        return f"{__class__.__name__}('{self.address}')"

    def __str__(self):
        return str(self.address)

    @staticmethod
    def enter_amount(multiple, maximum):
        while True:
            try:
                entry = int(input(f"Enter an amount in multiples of {multiple}: "))
            except ValueError:
                continue
            else:
                if entry % multiple == 0 and entry <= maximum:
                    return entry

    @staticmethod
    def enter_card():
        while True:
            entry = input("Enter your card (number): ")
            if len(entry) == 8 and entry.isnumeric():
                if ldb.sql_query_fetchall(my_local_db, f"SELECT number FROM cards WHERE number = {entry}"):
                    return entry
                else:
                    print("Sorry your card is not compatible with this ATM")

    @staticmethod
    def enter_pin(atm_card_number):
        tries = 0
        while tries < 3:
            pin_entry = input("Enter your card pin: ")
            if len(pin_entry) == 4 and pin_entry.isnumeric():
                if pin_entry == ldb.sql_query_fetchall(my_local_db, f"SELECT pin FROM cards WHERE number = {atm_card_number}")[0][0]:
                    return True
            tries += 1
        print("Sorry, you have exceeded your maximum attempts. ")
        return False

    @staticmethod
    def retrieve_customer_data(atm_card_number):
        card_holder = ldb.sql_query_fetchall(my_local_db, f"SELECT holder_firstname, holder_lastname, pin FROM cards WHERE number = {atm_card_number}")[0]
        customer_record = ldb.sql_query_fetchall(my_local_db, f"SELECT * FROM customers WHERE firstname = '{card_holder[0]}' AND lastname = '{card_holder[1]}'")[0]
        current_account_records = ldb.sql_query_fetchall(my_local_db, f"SELECT number, currency, overdraft FROM current_accounts WHERE holder_firstname = '{customer_record[0]}' AND holder_lastname = '{customer_record[1]}'")
        savings_account_records = ldb.sql_query_fetchall(my_local_db, f"SELECT number, currency, overdraft FROM savings_accounts WHERE holder_firstname = '{customer_record[0]}' AND holder_lastname = '{customer_record[1]}'")
        business_account_records = ldb.sql_query_fetchall(my_local_db, f"SELECT number, currency, overdraft FROM business_accounts WHERE holder_firstname = '{customer_record[0]}' AND holder_lastname = '{customer_record[1]}'")
        customer = acc.Customer(customer_record[0], customer_record[1], customer_record[2])
        customer.add_card(acc.Card(atm_card_number, card_holder[2]))
        for record in current_account_records:
            customer.add_account(acc.CurrentAccount(record[0], record[1], record[2]), "Current Account")
        for record in savings_account_records:
            customer.add_account(acc.SavingsAccount(record[0], record[1], record[2]), 'Savings Account')
        for record in business_account_records:
            customer.add_account(acc.BusinessAccount(record[0], record[1], record[2]), 'Business Account')
        del card_holder, customer_record, current_account_records, savings_account_records, business_account_records
        return customer, customer.cards[0]

    @staticmethod
    def change_pin(atm_card):
        pin_entry_one = input("Enter a new four digit pin: ")
        pin_entry_two = input("Enter the pin again: ")
        if pin_entry_one == pin_entry_two:
            if len(pin_entry_one) == 4 and pin_entry_one.isnumeric():
                atm_card.set_pin(pin_entry_one)
            else:
                print("Sorry invalid entry. Try again")
        else:
            print("Sorry entries do not match. Try again")
        del pin_entry_one
        del pin_entry_two

    @staticmethod
    def user_selection(atm_screen, customer_options=None):
        if customer_options is not None:
            counter = 0
            for item in customer_options:
                atm_screen[str(counter)] = item
                counter += 1
        for key in sorted([int(num) for num in atm_screen.keys()]):
            print(f"Enter {key} for {atm_screen[str(key)]}")
        while True:
            screen_entry = input()
            if screen_entry in atm_screen.keys():
                return atm_screen.get(screen_entry)

    @staticmethod
    def display_balance(selected_accounts):
        total = 0.0
        for selected_account in selected_accounts:
            total += selected_account.balance()
        print(f"Your balance is {total}")

    @staticmethod
    def print_transactions(selected_account, trans_num):
        transaction_list = selected_account.return_transaction(trans_num)
        for transaction in transaction_list:
            print(f"{transaction[1]} {transaction[2]} {transaction[3].upper()} on {transaction[5].strftime('%d-%b-%Y')}")


if __name__ == "__main__":
    # Connect to local MySql server and pull customer list to display in console
    my_local_db = ldb.initialise_local_db_connection('bank')
    for card in ldb.sql_query_fetchall(my_local_db, "SELECT * FROM cards"):
        print(f"Customer {card[4]} {card[5]} has a card with number {card[0]} and pin {card[1]}")

    # Create new ATM object
    atm = Atm("Ealing Broadway")

    # Run ATM program -> user must enter card number as proxy for swiping card
    network_card = atm.enter_card()
    verified = atm.enter_pin(network_card)
    while True:
        if not verified:
            break
        else:
            verified_card_holder, verified_card = atm.retrieve_customer_data(network_card)
            print("Select an account type: ")
            account_type_selection = atm.user_selection(atm.account_types_screen, verified_card_holder.accounts)
            if account_type_selection == atm.account_types_screen['5']:
                atm.change_pin(verified_card)
            elif account_type_selection == atm.account_types_screen['6']:
                atm.display_balance([account for accounts in verified_card_holder.accounts.values() for account in accounts])
            elif account_type_selection == atm.account_types_screen['7']:
                break
            else:
                print("Select an account: ")
                account_selection = atm.user_selection(atm.accounts_screen, verified_card_holder.accounts[account_type_selection])
                if account_selection == atm.accounts_screen['6']:
                    atm.display_balance([item for item in verified_card_holder.accounts[account_type_selection]])
                elif account_selection == atm.accounts_screen['7']:
                    pass
                else:
                    print("Select an activity: ")
                    activity_selection = atm.user_selection(atm.activity_screen)
                    if activity_selection == atm.activity_screen['4']:
                        verified_card.link_account(account_selection)
                        print(f"Your card is linked to {account_type_selection} {account_selection}")
                    elif activity_selection == atm.activity_screen['5']:
                        atm.print_transactions(account_selection, 10)
                    elif activity_selection == atm.activity_screen['6']:
                        print(f"Your balance is {account_selection.currency} {account_selection.balance()}")
                    elif activity_selection == atm.activity_screen['7']:
                        pass
                    elif activity_selection == atm.activity_screen['1']:
                        print("Select an amount: ")
                        amount_selection = atm.user_selection(atm.withdraw_screen)
                        if amount_selection == atm.withdraw_screen['7']:
                            pass
                        else:
                            debit_cash = account_selection.add_transaction(amount_selection, activity_selection.lower(), 'atm')
                            if not debit_cash:
                                print("Insufficient Funds")
                            if atm.atm_fee is not None:
                                account_selection.add_transaction(atm.atm_fee, activity_selection.lower(), 'fee', 'atm fee')
                    elif activity_selection == atm.activity_screen['2']:
                        amount_selection = atm.enter_amount(10, 250)
                        account_selection.add_transaction(amount_selection, activity_selection.lower(), 'atm')
                    elif activity_selection == atm.activity_screen['3']:
                        amount_selection = atm.enter_amount(10, 250)
                        debit_cash = account_selection.add_transaction(amount_selection, 'debit', 'atm')
                        if not debit_cash:
                            print("Insufficient Funds")
                        else:
                            account_selection.add_transaction(amount_selection, 'credit', 'tfr', 'account to account transfer')
    print("Thank you for using Sainsbury's ATM. See you again soon.")
