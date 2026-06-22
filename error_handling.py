# try:
#     x = 10 / 2
# except ZeroDivisionError:
#     print("You can't divide by zero!")
# else:
#     print('Division successful:', x)
# finally:
#     print('This block always runs.')

# try:
#     number = int('abc')
#     result = 10 / number
# except ValueError:
#     print('That was not a valid number.')
# except ZeroDivisionError:
#     print("Can't divide by zero.")

# try:
#     x = 1 / 0
# except ZeroDivisionError as e:
#     print(f'Error occurred: {e}')

try:
    number = int(input("Enter an interger number:"))
    y= 10/number
except (ValueError, ZeroDivisionError) as e:
    print(f'The error is: {e}')