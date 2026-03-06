---
name: 'C# Coding Standards'
description: 'Coding conventions and best practices for C# files'
applyTo: '**/*.cs'
---

<!-- 
This is a reference template for file-based instructions.
Instructions are automatically applied to files matching the applyTo glob pattern.
Teams can customize this file with Vancity-specific C# standards.
-->

# C# Coding Standards

When working with C# code, follow these conventions:

## Naming Conventions
- Use PascalCase for class names, method names, and public properties
- Use camelCase for local variables and private fields
- Prefix private fields with underscore: `_fieldName`
- Use meaningful, descriptive names

## Code Organization
- Place using directives outside namespace declarations
- Group using directives: System namespaces first, then third-party, then project namespaces
- One class per file
- Order members: fields, constructors, properties, methods

## Best Practices
- Use `var` when the type is obvious from the right side
- Use string interpolation over string concatenation
- Prefer expression-bodied members for simple properties and methods
- Use nullable reference types to prevent null reference exceptions
- Add XML documentation comments for public APIs

## Async/Await
- Suffix async methods with `Async`
- Always await async methods, don't use `.Result` or `.Wait()`
- Use `ConfigureAwait(false)` in library code

## Example
```csharp
public class OrderService
{
    private readonly IOrderRepository _orderRepository;
    
    public OrderService(IOrderRepository orderRepository)
    {
        _orderRepository = orderRepository ?? throw new ArgumentNullException(nameof(orderRepository));
    }
    
    public async Task<Order?> GetOrderByIdAsync(int orderId)
    {
        return await _orderRepository.FindByIdAsync(orderId).ConfigureAwait(false);
    }
}
```
