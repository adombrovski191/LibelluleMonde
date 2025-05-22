def find_closest_sum_to_zero(arr):
    """
    Find two numbers from the array whose sum is closest to zero.
    
    Time Complexity Analysis:
    - Sorting the array: O(n log n) where n is the length of the array
    - Two-pointer traversal: O(n) as we visit each element at most once
    - Overall Time Complexity: O(n log n) dominated by the sorting step
    
    Space Complexity Analysis:
    - Sorting in Python uses O(n) space for the TimSort algorithm
    - Additional variables (left, right, min_sum, result): O(1)
    - Overall Space Complexity: O(n) due to sorting
    
    Args:
        arr (list): List of integers
        
    Returns:
        tuple: Two numbers whose sum is closest to zero
    """
    if len(arr) < 2:
        raise ValueError("Array must contain at least 2 elements")
    
    # Sort the array to use two-pointer technique - O(n log n)
    arr.sort()
    
    # Initialize pointers and tracking variables - O(1) space
    left = 0
    right = len(arr) - 1
    min_sum = float('inf')
    result = (None, None)
    
    # Two-pointer traversal - O(n) time
    while left < right:
        current_sum = arr[left] + arr[right]
        
        # Update result if current sum is closer to zero - O(1)
        if abs(current_sum) < abs(min_sum):
            min_sum = current_sum
            result = (arr[left], arr[right])
        
        # Move pointers based on the sum - O(1)
        if current_sum < 0:
            left += 1
        else:
            right -= 1
    
    return result

def get_numbers_from_user():
    """Get numbers from user input.
    Accepts both comma-separated numbers and array-like format with square brackets.
    Examples:
        - Comma-separated: 1,2,3,-4,5
        - Array format: [1,2,3,-4,5] or [-8, 4, 5, -10, 3]
    """
    print("\nEnter numbers in one of these formats:")
    print("- Comma-separated: 1,2,3,-4,5")
    print("- Array format: [1,2,3,-4,5] or [-8, 4, 5, -10, 3]")
    print("Or enter 'q' to quit:")
    
    while True:
        user_input = input("> ").strip()
        if user_input.lower() == 'q':
            return None
        
        try:
            # Handle array-like format
            if user_input.startswith('[') and user_input.endswith(']'):
                # Remove brackets and split by comma
                user_input = user_input[1:-1]
            
            # Convert input string to list of integers, handling comma separation
            numbers = [int(x.strip()) for x in user_input.split(',')]
            if len(numbers) < 2:
                print("Please enter at least 2 numbers!")
                continue
            return numbers
        except ValueError:
            print("Invalid input! Please enter numbers in one of these formats:")
            print("- Comma-separated: 1,2,3,-4,5")
            print("- Array format: [1,2,3,-4,5] or [-8, 4, 5, -10, 3]")

# Example usage
if __name__ == "__main__":
    print("Welcome to the Closest Sum to Zero Finder!")
    print("You can:")
    print("1. Enter numbers manually")
    print("2. See example test cases")
    print("3. Quit")
    
    while True:
        print("\nChoose an option (1-3):")
        choice = input("> ").strip()
        
        if choice == '1':
            numbers = get_numbers_from_user()
            if numbers:
                result = find_closest_sum_to_zero(numbers)
                print(f"\nArray: {numbers}")
                print(f"Numbers with sum closest to zero: {result}")
        
        elif choice == '2':
            # Test cases
            test_arrays = [
                [-8, 4, 5, -10, 3],
                [1, 60, -10, 70, -80, 85],
                [-1, 2, -3, 4, -5],
                [1, 2, 3, 4, 5],
                [-1, -2, -3, -4, -5]
            ]
            
            for arr in test_arrays:
                result = find_closest_sum_to_zero(arr)
                print(f"\nArray: {arr}")
                print(f"Numbers with sum closest to zero: {result}")
        
        elif choice == '3':
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice! Please enter 1, 2, or 3.") 
