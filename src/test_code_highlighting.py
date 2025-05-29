#!/usr/bin/env python3
"""
Test for code highlighting in markdown content.
"""

import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QComboBox,
)
from PySide6.QtCore import Qt


from airunner.gui.widgets.llm.contentwidgets.markdown_widget import MarkdownWidget
from airunner.utils.text.formatter_extended import FormatterExtended


class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Code Highlighting Test")
        self.resize(800, 600)

        # Create a central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        layout = QVBoxLayout(central_widget)

        # Language selector
        self.language_combo = QComboBox()
        self.language_combo.addItems(
            [
                "python",
                "javascript",
                "html",
                "css",
                "c++",
                "java",
                "bash",
                "json",
            ]
        )
        layout.addWidget(self.language_combo)

        # Test button
        test_button = QPushButton("Test Code Highlighting")
        test_button.clicked.connect(self.test_highlighting)
        layout.addWidget(test_button)

        # Markdown widget to display content
        self.markdown_widget = MarkdownWidget()
        layout.addWidget(self.markdown_widget)

        # Set initial content
        self.test_highlighting()

    def test_highlighting(self):
        language = self.language_combo.currentText()
        test_markdown = f"""
# Code Highlighting Test

This is a test of code highlighting with language: **{language}**

```{language}
{self.get_sample_code(language)}
```

And here's some regular text after the code block.

## Another example with no language specified

```
function noLanguage() {{
    console.log("This code block has no language specified");
}}
```

## Inline code

Here's some `inline code` that should be highlighted differently.
"""
        # Process with formatter
        formatted = FormatterExtended.format_content(test_markdown)
        self.markdown_widget.setContent(formatted["content"])

    def get_sample_code(self, language):
        samples = {
            "python": '''def factorial(n):
    """Calculate the factorial of n recursively"""
    if n <= 1:
        return 1
    else:
        return n * factorial(n - 1)

# Test the function
for i in range(5):
    print(f"Factorial of {i} is {factorial(i)}")

class TestClass:
    def __init__(self, name):
        self.name = name
    
    def greet(self):
        return f"Hello, {self.name}!"''',
            "javascript": """// Simple JavaScript function
function calculateSum(a, b) {
    return a + b;
}

// Arrow function example
const multiply = (a, b) => a * b;

// Class example
class Person {
    constructor(name, age) {
        this.name = name;
        this.age = age;
    }
    
    greet() {
        return `Hello, my name is ${this.name} and I am ${this.age} years old`;
    }
}

// Promise example
fetch('https://api.example.com/data')
    .then(response => response.json())
    .then(data => console.log(data))
    .catch(error => console.error('Error:', error));""",
            "html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sample HTML</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <header>
        <h1>Welcome to My Website</h1>
        <nav>
            <ul>
                <li><a href="#home">Home</a></li>
                <li><a href="#about">About</a></li>
                <li><a href="#contact">Contact</a></li>
            </ul>
        </nav>
    </header>
    
    <main>
        <section id="home">
            <h2>Home Section</h2>
            <p>This is the home section of the website.</p>
        </section>
    </main>
    
    <footer>
        <p>&copy; 2025 My Website</p>
    </footer>
    
    <script src="script.js"></script>
</body>
</html>""",
            "css": """/* Main styles */
body {
    font-family: Arial, sans-serif;
    line-height: 1.6;
    margin: 0;
    padding: 0;
    background-color: #f4f4f4;
    color: #333;
}

header {
    background-color: #35424a;
    color: #ffffff;
    padding: 20px;
    text-align: center;
}

nav ul {
    list-style: none;
    display: flex;
    justify-content: center;
}

nav ul li {
    margin: 0 15px;
}

nav ul li a {
    color: #ffffff;
    text-decoration: none;
}

/* Responsive design */
@media (max-width: 768px) {
    .container {
        width: 95%;
    }
}""",
            "c++": """#include <iostream>
#include <vector>
#include <string>

// A simple class definition
class Person {
private:
    std::string name;
    int age;
    
public:
    Person(std::string name, int age) : name(name), age(age) {}
    
    std::string getName() const {
        return name;
    }
    
    int getAge() const {
        return age;
    }
    
    void birthday() {
        age++;
        std::cout << name << " is now " << age << " years old!" << std::endl;
    }
};

// Main function
int main() {
    std::vector<Person> people;
    
    people.push_back(Person("Alice", 25));
    people.push_back(Person("Bob", 30));
    
    for (const auto& person : people) {
        std::cout << person.getName() << " is " << person.getAge() << " years old." << std::endl;
    }
    
    return 0;
}""",
            "java": """import java.util.ArrayList;
import java.util.List;

/**
 * Sample Java class demonstrating basic features
 */
public class Main {
    public static void main(String[] args) {
        // Create a list of people
        List<Person> people = new ArrayList<>();
        people.add(new Person("John", 25));
        people.add(new Person("Sarah", 30));
        
        // Print details using method reference
        people.forEach(Person::printDetails);
        
        // Calculate average age
        double averageAge = people.stream()
                .mapToInt(Person::getAge)
                .average()
                .orElse(0.0);
        
        System.out.println("Average age: " + averageAge);
    }
    
    static class Person {
        private String name;
        private int age;
        
        public Person(String name, int age) {
            this.name = name;
            this.age = age;
        }
        
        public String getName() {
            return name;
        }
        
        public int getAge() {
            return age;
        }
        
        public void printDetails() {
            System.out.println(name + " is " + age + " years old");
        }
    }
}""",
            "bash": '''#!/bin/bash

# A simple bash script
echo "Starting script..."

# Define variables
name="World"
current_date=$(date +%Y-%m-%d)

# Function definition
greet() {
    local person=$1
    echo "Hello, $person!"
}

# Loop example
for i in {1..5}; do
    echo "Iteration $i"
    sleep 1
done

# Conditional statement
if [ -d "/tmp" ]; then
    echo "/tmp directory exists"
else
    echo "/tmp directory does not exist"
fi

# Call function
greet $name

# Check process status
ps aux | grep "python" | grep -v "grep"

echo "Today's date is $current_date"
echo "Script completed"''',
            "json": """{
    "name": "Sample Project",
    "version": "1.0.0",
    "description": "A sample project configuration",
    "main": "index.js",
    "scripts": {
        "start": "node index.js",
        "test": "jest",
        "build": "webpack --mode production"
    },
    "dependencies": {
        "express": "^4.17.1",
        "mongoose": "^5.9.7",
        "react": "^17.0.2",
        "react-dom": "^17.0.2"
    },
    "devDependencies": {
        "jest": "^27.0.6",
        "webpack": "^5.40.0",
        "webpack-cli": "^4.7.2"
    },
    "repository": {
        "type": "git",
        "url": "https://github.com/username/sample-project.git"
    },
    "keywords": [
        "sample",
        "project",
        "configuration"
    ],
    "author": "Your Name",
    "license": "MIT"
}""",
        }

        return samples.get(
            language, "// No sample code available for this language"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
