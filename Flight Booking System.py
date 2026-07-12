class Flight:
    def __init__(self, flight_no, destination, seats):
        self.flight_no = flight_no
        self.destination = destination
        self.total_seats = seats
        self.available_seats = seats

    def book_seat(self):
        if self.available_seats > 0:
            self.available_seats -= 1
            return True
        return False

    def cancel_seat(self):
        if self.available_seats < self.total_seats:
            self.available_seats += 1

    def __str__(self):
        return (
            f"Flight: {self.flight_no}\n"
            f"Destination: {self.destination}\n"
            f"Available Seats: {self.available_seats}/{self.total_seats}"
        )


class Passenger:
    def __init__(self, name, passport):
        self.name = name
        self.passport = passport

    def __str__(self):
        return f"{self.name} (Passport: {self.passport})"


class Booking:
    booking_id = 1000

    def __init__(self, passenger, flight):
        Booking.booking_id += 1
        self.booking_id = Booking.booking_id
        self.passenger = passenger
        self.flight = flight

    def __str__(self):
        return (
            f"\nBooking ID: {self.booking_id}\n"
            f"Passenger: {self.passenger.name}\n"
            f"Flight: {self.flight.flight_no}\n"
            f"Destination: {self.flight.destination}"
        )


class FlightSystem:
    def __init__(self):
        self.flights = []
        self.bookings = []

    def add_flight(self, flight):
        self.flights.append(flight)

    def list_flights(self):
        print("\n------ Available Flights ------")
        for flight in self.flights:
            print(flight)
            print("-" * 30)

    def find_flight(self, flight_no):
        for flight in self.flights:
            if flight.flight_no == flight_no:
                return flight
        return None

    def book_flight(self):
        flight_no = input("Enter flight number: ")
        flight = self.find_flight(flight_no)

        if not flight:
            print("Flight not found.")
            return

        if not flight.book_seat():
            print("No seats available.")
            return

        name = input("Passenger name: ")
        passport = input("Passport number: ")

        passenger = Passenger(name, passport)
        booking = Booking(passenger, flight)

        self.bookings.append(booking)

        print("\nBooking successful!")
        print(booking)

    def cancel_booking(self):
        booking_id = int(input("Enter Booking ID: "))

        for booking in self.bookings:
            if booking.booking_id == booking_id:
                booking.flight.cancel_seat()
                self.bookings.remove(booking)
                print("Booking cancelled successfully.")
                return

        print("Booking not found.")

    def show_bookings(self):
        if not self.bookings:
            print("No bookings available.")
            return

        print("\n------ BOOKINGS ------")
        for booking in self.bookings:
            print(booking)
            print("-" * 30)


system = FlightSystem()

system.add_flight(Flight("KQ101", "Nairobi", 5))
system.add_flight(Flight("KQ202", "Mombasa", 3))
system.add_flight(Flight("KQ303", "Kisumu", 4))

while True:
    print("\n===== FLIGHT BOOKING SYSTEM =====")
    print("1. View Flights")
    print("2. Book Flight")
    print("3. Cancel Booking")
    print("4. View Bookings")
    print("5. Exit")

    choice = input("Choose an option: ")

    if choice == "1":
        system.list_flights()

    elif choice == "2":
        system.book_flight()

    elif choice == "3":
        system.cancel_booking()

    elif choice == "4":
        system.show_bookings()

    elif choice == "5":
        print("Thank you for using the Flight Booking System.")
        break

    else:
        print("Invalid option.")