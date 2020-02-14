import random
import mysql.connector
import datetime


def initialise_local_db_connection(db_selection):
    return mysql.connector.connect(host="localhost", user="root", passwd="Tutti792!@#$", database=db_selection,)


def sql_query_fetchall(my_db, my_sql_query):
    my_cursor = my_db.cursor()
    my_cursor.execute(my_sql_query)
    return my_cursor.fetchall()


def sql_query_commit(my_db, my_sql_query, variables):
    my_cursor = my_db.cursor()
    my_cursor.execute(my_sql_query, variables)
    my_db.commit()


if __name__ == "__main__":
    my_local_db = initialise_local_db_connection('bank')
    my_cursor = my_local_db.cursor()

    # Drop prior version of tables
    my_cursor.execute("DROP TABLE transactions")
    my_cursor.execute("DROP TABLE cards")
    my_cursor.execute("DROP TABLE accounts")
    my_cursor.execute("DROP TABLE current_accounts")
    my_cursor.execute("DROP TABLE savings_accounts")
    my_cursor.execute("DROP TABLE business_accounts")
    my_cursor.execute("DROP TABLE customers")
    my_cursor.execute("DROP TABLE branches")
    my_cursor.execute("DROP TABLE networks")
    my_cursor.execute("DROP TABLE banks")

    # Create tables for fake data
    my_cursor.execute(
        '''CREATE TABLE banks (
        name VARCHAR(255) NOT NULL, parent VARCHAR(255), 
        PRIMARY KEY (name)
        )'''
    )
    my_cursor.execute(
        '''CREATE TABLE networks (
        name VARCHAR(255) NOT NULL, bank_name VARCHAR(255) NOT NULL, 
        PRIMARY KEY (name), 
        FOREIGN KEY (bank_name) REFERENCES banks(name)
        )'''
    )
    my_cursor.execute(
        '''CREATE TABLE branches (
        address1 VARCHAR(255), sortcode INT(6) NOT NULL, bank_name VARCHAR(255), 
        PRIMARY KEY (sortcode), 
        FOREIGN KEY (bank_name) REFERENCES banks(name)
        )'''
    )
    my_cursor.execute(
        '''CREATE TABLE customers (
        firstname VARCHAR(255) NOT NULL, lastname VARCHAR(255) NOT NULL, overdraft DECIMAL(10,2), branch_sortcode INT(6), 
        CONSTRAINT fullname_pk PRIMARY KEY (firstname, lastname), 
        FOREIGN KEY (branch_sortcode) REFERENCES branches(sortcode)
        )'''
    )
    my_cursor.execute(
        '''CREATE TABLE current_accounts(
        number VARCHAR(8) NOT NULL, currency VARCHAR(3) NOT NULL, overdraft DECIMAL(10,2), holder_firstname VARCHAR(255), holder_lastname VARCHAR(255), 
        PRIMARY KEY (number), 
        CONSTRAINT holder_current_fk FOREIGN KEY (holder_firstname, holder_lastname) REFERENCES customers(firstname, lastname)
        )'''
    )
    my_cursor.execute(
        '''CREATE TABLE savings_accounts(
        number VARCHAR(8) NOT NULL, currency VARCHAR(3) NOT NULL, overdraft DECIMAL(10,2), holder_firstname VARCHAR(255), holder_lastname VARCHAR(255), 
        PRIMARY KEY (number), 
        CONSTRAINT holder_savings_fk FOREIGN KEY (holder_firstname, holder_lastname) REFERENCES customers(firstname, lastname)
        )'''
    )
    my_cursor.execute(
        '''CREATE TABLE business_accounts(
        number VARCHAR(8) NOT NULL, currency VARCHAR(3) NOT NULL, overdraft DECIMAL(10,2), holder_firstname VARCHAR(255), holder_lastname VARCHAR(255), 
        PRIMARY KEY (number), 
        CONSTRAINT holder_business_fk FOREIGN KEY (holder_firstname, holder_lastname) REFERENCES customers(firstname, lastname)
        )'''
    )
    my_cursor.execute(
        '''CREATE TABLE accounts(
        account_id VARCHAR(8), current_accounts_id VARCHAR(8), savings_accounts_id VARCHAR(8), business_accounts_id VARCHAR(8), 
        PRIMARY KEY (account_id), 
        CONSTRAINT current_accounts_fk FOREIGN KEY (current_accounts_id) REFERENCES current_accounts(number), CONSTRAINT savings_accounts_fk FOREIGN KEY (savings_accounts_id) REFERENCES savings_accounts(number), CONSTRAINT business_accounts_fk FOREIGN KEY (business_accounts_id) REFERENCES business_accounts(number)
        )'''
    )
    my_cursor.execute(
        '''CREATE TABLE cards(
        number VARCHAR(8) NOT NULL, pin VARCHAR(4) NOT NULL, expiry_date DATE NOT NULL, linked_account VARCHAR(8), holder_firstname VARCHAR(255), holder_lastname VARCHAR(255), 
        CONSTRAINT card_pk PRIMARY KEY (number, expiry_date, holder_firstname, holder_lastname), 
        CONSTRAINT account_fk FOREIGN KEY (linked_account) REFERENCES accounts(account_id), 
        CONSTRAINT holder_card_fk FOREIGN KEY (holder_firstname, holder_lastname) REFERENCES customers(firstname, lastname)
        )'''
    )
    my_cursor.execute(
        '''CREATE TABLE transactions(
        account_id VARCHAR(8) NOT NULL, amount DECIMAL(10,2) NOT NULL, type VARCHAR(6) NOT NULL, category VARCHAR(3), description VARCHAR(255), date_time DATETIME NOT NULL, 
        CONSTRAINT transaction_pk PRIMARY KEY (account_id, type, date_time), 
        FOREIGN KEY (account_id) REFERENCES accounts(account_id)
        )'''
    )

    # # Create fake bank, branch and customer data
    networks = [('link', 'Crappy bank')]
    banks = [('Crappy bank', 'Crappy plc')]
    branches = [('Cornhill', 204060, 'Crappy bank')]
    new_customers = [('Marky', 'Mark', 1000, 204060), ('Donnie', 'Dee', 2500, 204060), ('Rizzle', 'Pizzle', 0, 204060)]
    accounts = ['current_accounts', 'savings_accounts', 'business_accounts']

    # Add records to tables (card records initially linked to current accounts)
    for bank in banks:
        my_cursor.execute("INSERT INTO banks (name, parent) VALUES (%s, %s)", (bank[0], bank[1]))

    for network in networks:
        my_cursor.execute("INSERT INTO networks (name, bank_name) VALUES (%s, %s)", (network[0], network[1]))

    for branch in branches:
        my_cursor.execute("INSERT INTO branches (address1, sortcode, bank_name) VALUES (%s, %s, %s)", (branch[0], branch[1], branch[2]))

    for new_customer in new_customers:
        my_cursor.execute("INSERT INTO customers (firstname, lastname, overdraft, branch_sortcode) VALUES (%s, %s, %s, %s)", (new_customer[0], new_customer[1], new_customer[2], new_customer[3]))
        for account in accounts:
            random_num = str(random.randint(10000000, 99999999))
            my_cursor.execute(f"INSERT INTO {account} (number, currency, overdraft, holder_firstname, holder_lastname) VALUES ({random_num}, 'gbp', {random.randint(0, 1000)}, '{new_customer[0]}', '{new_customer[1]}')")
            my_cursor.execute(f"INSERT INTO accounts (account_id, {account + '_id'}) VALUES ({random_num}, {random_num})")
            if account == 'current_accounts':
                random_card_num = str(random.randint(10000000, 99999999))
                my_cursor.execute("INSERT INTO cards (number, pin, expiry_date, linked_account, holder_firstname, holder_lastname) VALUES (%s, %s, %s, %s, %s, %s)", (random_card_num, 9999, datetime.date.today() + datetime.timedelta(days=365*3), random_num, new_customer[0], new_customer[1]))

    my_local_db.commit()
