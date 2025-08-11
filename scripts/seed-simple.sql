-- Simple demo data for NeuroBridgeEDU

-- Insert demo students
INSERT OR IGNORE INTO students (name, api_endpoint, active) VALUES 
    ('Demo Student 1', 'https://httpbin.org/post', 1),
    ('Demo Student 2', 'https://webhook.site/unique-id', 1),
    ('Test Integration', 'https://api.example.com/webhook', 0),
    ('Mock Student API', 'https://jsonplaceholder.typicode.com/posts', 1);

-- Insert sample summaries
INSERT OR IGNORE INTO summaries (title, content, raw_transcript, metadata) VALUES 
    (
        'Introduction to AI - Sample Lecture',
        '# AI Fundamentals\n\n## Overview\nIntroduction to artificial intelligence concepts and applications.\n\n## Key Concepts\n- Machine Learning basics\n- Neural networks\n- Real-world applications\n\n## Action Items\n- Read chapters 1-3\n- Complete online exercises',
        'Welcome to AI fundamentals. Today we will cover basic concepts of artificial intelligence...',
        '{"duration": 3600, "word_count": 120, "topic": "AI Introduction"}'
    ),
    (
        'Database Design - Normalization',
        '# Database Normalization\n\n## Overview\nPrinciples of database design and normalization forms.\n\n## Key Concepts\n- First Normal Form (1NF)\n- Second Normal Form (2NF)\n- Third Normal Form (3NF)\n\n## Assignment\n- Complete normalization exercise',
        'Today we explore database normalization principles and best practices...',
        '{"duration": 2700, "word_count": 95, "topic": "Database Design"}'
    );

-- Insert sample send logs
INSERT OR IGNORE INTO send_logs (summary_id, student_id, status, response_code, retry_count) VALUES
    (1, 1, 'sent', 200, 0),
    (1, 2, 'sent', 200, 0),
    (2, 1, 'sent', 200, 0),
    (2, 3, 'failed', 500, 2);