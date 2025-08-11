-- Demo data seeding for NeuroBridgeEDU
-- This file contains sample data for testing and demonstration

-- Insert demo students for testing various API endpoints
INSERT OR IGNORE INTO students (name, api_endpoint, email, active, webhook_secret, rate_limit_per_hour) VALUES 
    ('Demo Student - HTTPBin', 'https://httpbin.org/post', 'demo1@example.com', 1, 'demo_secret_123', 100),
    ('Demo Student - Webhook.site', 'https://webhook.site/unique-id-here', 'demo2@example.com', 1, 'demo_secret_456', 60),
    ('Test Integration - Disabled', 'https://api.example.com/webhook', 'test@example.com', 0, 'test_secret_789', 30),
    ('Mock Student API', 'https://jsonplaceholder.typicode.com/posts', 'mock@example.com', 1, 'mock_secret_abc', 80),
    ('Local Development', 'http://localhost:8080/webhook', 'dev@localhost', 1, 'dev_secret_xyz', 1000);

-- Insert sample summaries for demo purposes
INSERT OR IGNORE INTO summaries (title, content, raw_transcript, status, topic_category, duration_seconds, ai_confidence_score, metadata) VALUES 
    (
        'Introduction to Artificial Intelligence - Lecture 1', 
        '# AI Fundamentals - Lecture Summary

## Overview
This introductory lecture covered the fundamental concepts of artificial intelligence, providing students with a solid foundation for understanding AI systems and their applications.

## Key Concepts Covered

### 1. Definition of Artificial Intelligence
- AI as the simulation of human intelligence in machines
- Difference between narrow AI and general AI
- Current state of AI technology in 2024

### 2. Machine Learning Basics
- Supervised vs unsupervised learning
- Training data and model development
- Common algorithms: linear regression, decision trees, neural networks

### 3. Neural Networks Introduction
- Biological inspiration from human brain
- Artificial neurons and layers
- Forward propagation and backpropagation
- Deep learning as extension of neural networks

### 4. Real-world Applications
- Computer vision (image recognition, object detection)
- Natural language processing (chatbots, translation)
- Recommendation systems (Netflix, Amazon)
- Autonomous vehicles and robotics

## Action Items for Students
1. **Reading Assignment**: Complete Chapters 1-3 in "AI: A Modern Approach"
2. **Online Practice**: Finish the interactive exercises on the course portal
3. **Research Task**: Find and analyze one current AI application in your field of interest
4. **Discussion Forum**: Post your thoughts on the ethical implications of AI

## Key Terms to Remember
- **Artificial Intelligence**: Computer systems that can perform tasks requiring human intelligence
- **Machine Learning**: Subset of AI that enables computers to learn without explicit programming
- **Neural Network**: Computing system inspired by biological neural networks
- **Algorithm**: Step-by-step procedure for solving a problem

## Next Lecture Preview
Next week we will dive deeper into machine learning algorithms and explore hands-on programming exercises using Python and popular ML libraries.',
        
        'Welcome everyone to Introduction to Artificial Intelligence, this is our first lecture of the semester. Today we are going to cover the fundamental concepts that will serve as the foundation for everything else we learn this term. Let me start by asking - what do you think artificial intelligence actually means? I see some hands... Yes, Sarah? Good point about machines thinking like humans. That is certainly part of it, but let me give you a more precise definition. Artificial Intelligence is the field of computer science focused on creating systems that can perform tasks that would normally require human intelligence. This includes things like learning, reasoning, problem-solving, perception, and language understanding. Now, it is important to distinguish between what we call narrow AI and general AI. Narrow AI, which is what we have today, is designed to perform specific tasks very well - like playing chess, recognizing faces in photos, or translating languages. General AI, which does not exist yet, would be a system that could perform any intellectual task that a human can do. Most experts believe we are still decades away from achieving general AI. Let us talk about machine learning, which is really the engine driving most of the AI advances we see today. Machine learning is a subset of AI that enables computers to learn and improve from experience without being explicitly programmed for every possible scenario. There are two main types: supervised learning, where we train the system using labeled examples, and unsupervised learning, where the system finds patterns in data without being told what to look for. The key insight is that instead of programming every rule, we let the computer discover the patterns in the data. This brings us to neural networks, which are inspired by how our brains work. Just like our brain has billions of neurons connected together, artificial neural networks have artificial neurons arranged in layers. Information flows from the input layer through hidden layers to the output layer. The magic happens through a process called backpropagation, where the network adjusts its connections based on the errors it makes. When we have many layers, we call this deep learning. Now let me show you some real-world applications that you probably use every day. Computer vision powers the face recognition in your smartphone cameras and the object detection in autonomous vehicles. Natural language processing enables chatbots, language translation services, and voice assistants like Siri or Alexa. Recommendation systems analyze your behavior to suggest movies on Netflix or products on Amazon. These are all examples of narrow AI working behind the scenes. For your homework this week, I want you to read the first three chapters of our textbook, complete the online exercises I have posted, and think about how AI might be applied in your own field of study. We will start next week with hands-on programming exercises using Python. Are there any questions before we wrap up?',
        
        'published',
        'Computer Science',
        3600,
        0.92,
        '{"duration": 3600, "word_count": 520, "topic": "AI Introduction", "course_code": "CS101", "professor": "Dr. Smith", "semester": "Fall 2024"}'
    ),
    
    (
        'Database Design Principles - Normalization',
        '# Database Design - Normalization Forms

## Lecture Overview
Today we explored the fundamental principles of database normalization, focusing on how to design efficient and maintainable database schemas.

## Key Learning Objectives
- Understand the problems that normalization solves
- Learn the first three normal forms (1NF, 2NF, 3NF)
- Apply normalization techniques to real-world examples
- Recognize when denormalization might be appropriate

## Core Concepts

### Database Anomalies
- **Insert Anomaly**: Cannot add data without including unrelated information
- **Update Anomaly**: Must update multiple rows for a single logical change
- **Delete Anomaly**: Losing important data when deleting a row

### First Normal Form (1NF)
- Each column contains atomic (indivisible) values
- No repeating groups or arrays in columns
- Each row must be unique

### Second Normal Form (2NF)
- Must be in 1NF
- All non-key attributes must be fully functionally dependent on the primary key
- Eliminates partial dependencies

### Third Normal Form (3NF)
- Must be in 2NF
- No transitive dependencies (non-key attributes should not depend on other non-key attributes)
- Each non-key attribute depends only on the primary key

## Practical Example: Student Enrollment System

### Before Normalization (Problems)
```
Student_Course (StudentID, StudentName, CourseID, CourseName, Instructor, Grade)
```
Issues: Redundancy, update anomalies, storage waste

### After Normalization (3NF)
```
Students (StudentID, StudentName)
Courses (CourseID, CourseName, Instructor)  
Enrollments (StudentID, CourseID, Grade)
```

## Assignment for Next Week
1. Complete normalization exercise with the library database
2. Read Chapter 7: "Advanced Normalization Techniques"
3. Submit your normalized schema for the e-commerce project

## Quiz Next Class
Be prepared for a quiz covering 1NF, 2NF, and 3NF with practical examples.',

        'Good morning class, today we are diving into one of the most important topics in database design: normalization. Who can tell me what problems we might encounter if we do not design our database tables properly? Yes, exactly - we get redundant data, inconsistent updates, and wasted storage space. These are called database anomalies, and normalization is our systematic approach to eliminating them. Let me show you an example of a poorly designed table and we will work through normalizing it together. Imagine we have a table called Student_Course that contains StudentID, StudentName, CourseID, CourseName, Instructor, and Grade all in one table. What problems do you see here? Right, if we want to add a new course, we cannot do it unless a student enrolls in it. That is an insert anomaly. If an instructor changes their name, we have to update it in multiple rows. That is an update anomaly. And if we delete the last student from a course, we lose all information about that course. That is a delete anomaly. The solution is normalization. First Normal Form, or 1NF, requires that each column contains atomic values - no lists or arrays. Each row must also be unique. Second Normal Form, 2NF, eliminates partial dependencies. This means every non-key column must depend on the entire primary key, not just part of it. Third Normal Form, 3NF, eliminates transitive dependencies where non-key columns depend on other non-key columns instead of the primary key. Let me show you how we would normalize our Student_Course table. We would split it into three tables: Students with StudentID and StudentName, Courses with CourseID, CourseName and Instructor, and Enrollments linking students to courses with grades. This eliminates all our anomalies and makes the database much more maintainable. Your assignment for next week is to practice this with the library database example I am giving you, and there will be a quiz on these concepts at the start of next class.',

        'published',
        'Database Systems', 
        2700,
        0.88,
        '{"duration": 2700, "word_count": 420, "topic": "Database Normalization", "course_code": "CS202", "professor": "Dr. Johnson", "semester": "Fall 2024"}'
    ),
    
    (
        'Web Security Best Practices - OWASP Top 10',
        '# Web Security Fundamentals

## Session Overview
Critical examination of the OWASP Top 10 web application security risks and implementation of defensive programming techniques.

## OWASP Top 10 2024 Highlights

### A01: Broken Access Control
- Implement proper authorization checks
- Principle of least privilege
- Regular access reviews and audits

### A02: Cryptographic Failures
- Use strong encryption algorithms
- Proper key management practices
- Secure data transmission (HTTPS)

### A03: Injection Attacks
- Input validation and sanitization
- Parameterized queries for SQL injection prevention
- Content Security Policy for XSS mitigation

### A04: Insecure Design
- Security by design principles
- Threat modeling during development
- Secure architecture patterns

## Practical Security Implementation

### Input Validation Strategy
```javascript
// Example: Secure input validation
function validateUserInput(input) {
    // Whitelist approach
    const allowedPattern = /^[a-zA-Z0-9\s]{1,100}$/;
    return allowedPattern.test(input);
}
```

### Authentication Best Practices
- Multi-factor authentication
- Strong password policies
- Session management security
- Secure password storage (bcrypt with 14+ rounds)

### Authorization Patterns
- Role-Based Access Control (RBAC)
- Attribute-Based Access Control (ABAC)
- Principle of least privilege implementation

## Lab Assignment
1. Conduct security audit of provided web application
2. Implement input validation for all user inputs
3. Add proper authentication and authorization
4. Document security measures and test results

## Required Reading
- OWASP Top 10 2024 documentation
- "Web Application Security" Chapter 12-15
- Latest security bulletins and CVE reports

## Next Week: Penetration Testing Fundamentals',

        'Welcome to our web security lecture, one of the most critical topics for any developer in 2024. The cyber threat landscape has evolved dramatically, and web applications remain the primary attack vector for malicious actors. Today we are going to dive deep into the OWASP Top 10, which represents the most critical web application security risks based on real-world data from security organizations worldwide. Let us start with the number one risk: Broken Access Control. This occurs when users can access resources or perform actions they should not be authorized to do. Think about it - what if a regular user could access admin panels, or view other users private data? This happens more often than you might think. The solution is implementing proper authorization checks at every level, following the principle of least privilege, and conducting regular access reviews. Next is Cryptographic Failures, which used to be called Sensitive Data Exposure. This involves failures related to cryptography that can lead to data breaches. Are you storing passwords in plain text? Using weak encryption algorithms? Not implementing HTTPS properly? These are all cryptographic failures. Always use strong, up-to-date encryption algorithms, implement proper key management, and ensure all data transmission is secure. Injection attacks, our third risk, remain a persistent threat. SQL injection, cross-site scripting, command injection - these occur when untrusted data is processed without proper validation. The defense is simple in concept but requires discipline: always validate and sanitize user inputs, use parameterized queries, and implement content security policies. Insecure Design is a newer category that focuses on risks related to design and architectural flaws. This is about building security into your application from the ground up, not trying to bolt it on later. We need to think like attackers during the design phase, conduct threat modeling, and use proven secure architecture patterns. For your lab assignment this week, you will be conducting a security audit of a web application I have prepared that contains several of these vulnerabilities. Your job is to identify them, implement proper fixes, and document your security measures. Remember, security is not a feature you add at the end - it must be woven into every aspect of your development process.',

        'draft',
        'Cybersecurity',
        3300,
        0.95,
        '{"duration": 3300, "word_count": 480, "topic": "Web Security", "course_code": "SEC301", "professor": "Dr. Williams", "semester": "Fall 2024"}'
    );

-- Insert sample send logs to demonstrate delivery tracking
INSERT OR IGNORE INTO send_logs (summary_id, student_id, status, response_code, response_body, retry_count) VALUES
    (1, 1, 'sent', 200, '{"message": "Webhook received successfully", "timestamp": "2024-07-31T10:30:00Z"}', 0),
    (1, 2, 'sent', 200, '{"status": "ok", "id": "webhook-123"}', 0),
    (1, 4, 'failed', 500, '{"error": "Internal server error"}', 2),
    (2, 1, 'sent', 200, '{"message": "Webhook received successfully", "timestamp": "2024-07-31T11:15:00Z"}', 0),
    (2, 2, 'pending', NULL, NULL, 0),
    (3, 1, 'sent', 200, '{"message": "Webhook received successfully", "timestamp": "2024-07-31T12:00:00Z"}', 0);

-- Insert application settings
INSERT OR IGNORE INTO app_settings (setting_key, setting_value, description) VALUES
    ('app_version', '1.0.0', 'Current application version'),
    ('max_summary_length', '10000', 'Maximum character length for summary content'),
    ('default_ai_model', 'gpt-4.1-mini', 'Default AI model for content generation'),
    ('webhook_timeout_seconds', '30', 'Timeout for webhook delivery attempts'),
    ('max_retry_attempts', '3', 'Maximum number of retry attempts for failed deliveries'),
    ('enable_demo_mode', 'true', 'Enable demonstration mode with sample data'),
    ('api_rate_limit_per_hour', '100', 'Default API rate limit per hour'),
    ('auto_backup_enabled', 'true', 'Enable automatic database backups'),
    ('backup_retention_days', '30', 'Number of days to retain backup files'),
    ('log_level', 'info', 'Application logging level (debug, info, warn, error)');

-- Insert some sample API usage data for monitoring
INSERT OR IGNORE INTO api_usage (endpoint, method, status_code, response_time_ms, user_agent, ip_address) VALUES
    ('/api/summaries', 'GET', 200, 45, 'Mozilla/5.0 (compatible; Demo)', '127.0.0.1'),
    ('/api/summaries', 'POST', 201, 120, 'Mozilla/5.0 (compatible; Demo)', '127.0.0.1'),
    ('/api/students', 'GET', 200, 32, 'Mozilla/5.0 (compatible; Demo)', '127.0.0.1'),
    ('/api/students/1/send', 'POST', 200, 1500, 'Mozilla/5.0 (compatible; Demo)', '127.0.0.1'),
    ('/health', 'GET', 200, 5, 'Docker Health Check', '172.17.0.1'),
    ('/health', 'GET', 200, 3, 'Docker Health Check', '172.17.0.1');