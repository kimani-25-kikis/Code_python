class Primary:
    def __init__(self, content):
        self.content = content
    def description(self):
        return f'We offer best {self.content} certificates'
    
class Secondary:
    def __init__(self, content):
        self.content = content
    def description(self):
        return f'We offer best {self.content} certificates'
    
class University:
    def __init__(self, content):
        self.content = content
    def description(self):
        return f'We offer best {self.content} certificates'
def education(institution):
    print(institution.description())
pry= Primary("KCPE")
scy= Primary("KCSE")
uni= Primary("Degree")

education(pry)
education(scy)
education(uni)