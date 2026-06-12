# languages =['Swahili', 'Kikuyu','Luhya']

# for index, language in enumerate(languages):
#     print(f'{index} {language}')

numbers = [1,2,3,4,5,6,7,8,9]

result = [(num, 'even') if num % 2==0 else (num, 'odd') for num in numbers]
print(result)