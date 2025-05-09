import requests
import time
import statistics
from datetime import datetime
import json

def monitor_endpoint(url, iterations=1000):
    response_times = []
    errors = []
    counter_values = []
    start_time = datetime.now()
    
    print(f"Starting monitoring at {start_time}")
    print(f"Target URL: {url}")
    print(f"Number of iterations: {iterations}")
    print("-" * 50)
    
    for i in range(iterations):
        try:
            start = time.time()
            response = requests.get(url)
            end = time.time()
            
            response_time = (end - start) * 1000  # Convert to milliseconds
            response_times.append(response_time)
            
            if response.status_code == 200:
                counter_value = response.json().get('counter', 0)
                counter_values.append(counter_value)
                
                if i > 0 and counter_value != counter_values[-2] + 1:
                    errors.append({
                        'iteration': i,
                        'expected': counter_values[-2] + 1,
                        'received': counter_value
                    })
            else:
                errors.append({
                    'iteration': i,
                    'status_code': response.status_code,
                    'response': response.text
                })
                
        except Exception as e:
            errors.append({
                'iteration': i,
                'error': str(e)
            })
        
        if (i + 1) % 100 == 0:
            print(f"Completed {i + 1} iterations...")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    # Calculate statistics
    stats = {
        'total_iterations': iterations,
        'successful_requests': len(response_times),
        'failed_requests': len(errors),
        'average_response_time': statistics.mean(response_times),
        'median_response_time': statistics.median(response_times),
        'min_response_time': min(response_times),
        'max_response_time': max(response_times),
        'standard_deviation': statistics.stdev(response_times) if len(response_times) > 1 else 0,
        'total_duration': duration,
        'requests_per_second': iterations / duration,
        'errors': errors
    }
    
    # Print results
    print("\nMonitoring Results:")
    print("-" * 50)
    print(f"Total Duration: {duration:.2f} seconds")
    print(f"Successful Requests: {stats['successful_requests']}")
    print(f"Failed Requests: {stats['failed_requests']}")
    print(f"Average Response Time: {stats['average_response_time']:.2f} ms")
    print(f"Median Response Time: {stats['median_response_time']:.2f} ms")
    print(f"Min Response Time: {stats['min_response_time']:.2f} ms")
    print(f"Max Response Time: {stats['max_response_time']:.2f} ms")
    print(f"Standard Deviation: {stats['standard_deviation']:.2f} ms")
    print(f"Requests per Second: {stats['requests_per_second']:.2f}")
    
    if errors:
        print("\nErrors encountered:")
        for error in errors:
            print(json.dumps(error, indent=2))
    
    # Save results to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f'monitoring_results_{timestamp}.json', 'w') as f:
        json.dump(stats, f, indent=2)
    
    return stats

if __name__ == "__main__":
    monitor_endpoint("http://localhost:8080/counter") 