import database
import inventory
import orders

def main_menu():
    while True:
        print(f"\n ----- Main Menu -----")
        print("01: Generate A Quote")
        print("02: List Hero Products")
        print("03: List All Products")
        print("04: View Order History")
        print("05: Manage Inventory")
        print("99: Exit")

        choice = input("\nEnter Selection: ")

        match choice:
            case '01':
                orders.start_quote_flow()
            case '02' | '03':
                inventory.display_inventory_list(only_heroes=(choice == '02'))
            case '04':
                orders.order_history_manager()
            case '05':
                inventory.inventory_management_menu()
            case '99':
                print("Exiting...")
                break
            case _: print("Invalid choice, try again.")

if __name__ == "__main__":
    database.initialize_local_database()
    if database.check_setup():
        main_menu()