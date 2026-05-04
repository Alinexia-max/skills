# Java 代码审查参考

## 一、常见语法错误模式

### 1. 空指针相关
```java
// ❌ 错误
String str = getValue();
if (str.equals("test")) { ... }  // str 可能为 null

// ✅ 正确
String str = getValue();
if ("test".equals(str)) { ... }  // 或 Objects.equals()

// ❌ 错误 - 未判空直接拆箱
Integer count = getCount();
int c = count;  // count 为 null 时抛 NPE

// ✅ 正确
if (count != null) { int c = count; }
```

### 2. 资源未关闭
```java
// ❌ 错误
InputStream is = new FileInputStream("file.txt");
// 使用流... 但未关闭

// ✅ 正确（Java 7+）
try (InputStream is = new FileInputStream("file.txt")) {
    // 使用流
}
```

### 3. equals/hashCode 不匹配
```java
// ❌ 错误 - 只覆写 equals 未覆写 hashCode
@Override
public boolean equals(Object o) { ... }

// ✅ 正确 - 同时覆写两者
@Override
public boolean equals(Object o) { ... }

@Override
public int hashCode() { return Objects.hash(field1, field2); }
```

### 4. 集合遍历修改
```java
// ❌ 错误 - 遍历时直接 remove
for (String s : list) {
    if (s.startsWith("a")) {
        list.remove(s);  // ConcurrentModificationException
    }
}

// ✅ 正确 - 使用 Iterator
Iterator<String> it = list.iterator();
while (it.hasNext()) {
    if (it.next().startsWith("a")) {
        it.remove();
    }
}
// ✅ 或使用 removeIf（Java 8+）
list.removeIf(s -> s.startsWith("a"));
```

## 二、常见编码规范问题

### 1. 命名不规范
```java
// ❌ 错误
public class userinfo { ... }        // 类名应大驼峰
int a;                               // 变量名无意义
public final String str = "test";    // 常量应全大写

// ✅ 正确
public class UserInfo { ... }
int userId;
public static final String DEFAULT_NAME = "test";
```

### 2. 魔法数字
```java
// ❌ 错误
if (status == 1) { ... }
Thread.sleep(5000);

// ✅ 正确
private static final int STATUS_ACTIVE = 1;
private static final long TIMEOUT_MS = 5000L;
if (status == STATUS_ACTIVE) { ... }
Thread.sleep(TIMEOUT_MS);
```

### 3. 过长方法
```java
// ❌ 错误 - 方法超过 100 行，多个职责
public void processOrder(Order order) {
    // 50 行验证逻辑
    // 30 行计算逻辑
    // 40 行通知逻辑
}

// ✅ 正确 - 单一职责，每个方法 ≤ 30 行
public void processOrder(Order order) {
    validateOrder(order);
    calculatePrice(order);
    notifyCustomer(order);
}
```

### 4. switch 缺少 default
```java
// ❌ 错误
switch (type) {
    case A: handleA(); break;
    case B: handleB(); break;
}

// ✅ 正确
switch (type) {
    case A: handleA(); break;
    case B: handleB(); break;
    default: throw new IllegalArgumentException("未知类型: " + type);
}
```

## 三、常见性能优化模式

### 1. 字符串拼接
```java
// ❌ 错误
String result = "";
for (int i = 0; i < 1000; i++) {
    result += String.valueOf(i);  // 每次创建新对象
}

// ✅ 正确
StringBuilder sb = new StringBuilder(5000);
for (int i = 0; i < 1000; i++) {
    sb.append(i);
}
String result = sb.toString();
```

### 2. 循环中创建昂贵对象
```java
// ❌ 错误
for (Date date : dates) {
    SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd");  // 每次循环创建
    String str = sdf.format(date);
}

// ✅ 正确
private static final ThreadLocal<SimpleDateFormat> DATE_FORMAT =
    ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyy-MM-dd"));
for (Date date : dates) {
    String str = DATE_FORMAT.get().format(date);
}
```

### 3. Map 遍历方式
```java
// ❌ 错误
for (String key : map.keySet()) {
    String value = map.get(key);  // 二次查找
}

// ✅ 正确
for (Map.Entry<String, String> entry : map.entrySet()) {
    String key = entry.getKey();
    String value = entry.getValue();
}
// ✅ 或 Java 8+
map.forEach((key, value) -> { ... });
```

### 4. 集合初始容量
```java
// ❌ 错误 - 已知大小时未指定容量
List<String> list = new ArrayList<>();  // 默认 10
// 预期添加 10000 条，会多次扩容

// ✅ 正确
List<String> list = new ArrayList<>(10000);
Map<String, Object> map = new HashMap<>(1024);
// 注意 HashMap 负载因子 0.75
// 存放 n 条时初始容量应 ≥ n / 0.75 + 1
```

### 5. 循环中 List.contains
```java
// ❌ 错误 - O(n^2)
for (String item : items) {
    if (blackList.contains(item)) { ... }
}

// ✅ 正确 - O(n)
Set<String> blackSet = new HashSet<>(blackList);
for (String item : items) {
    if (blackSet.contains(item)) { ... }
}
```

### 6. 自动装箱/拆箱
```java
// ❌ 错误
Integer sum = 0;
for (int i = 0; i < 10000; i++) {
    sum += i;  // 每次拆箱 + 装箱
}

// ✅ 正确
int sum = 0;
for (int i = 0; i < 10000; i++) {
    sum += i;
}
```

### 7. 使用 stream 但数据量大
```java
// ❌ 错误 - 大数据量时使用 stream 有额外开销
list.stream().filter(x -> x > 10).collect(toList());

// ✅ 正确 - 简单过滤用普通循环更快
List<Integer> result = new ArrayList<>();
for (int x : list) {
    if (x > 10) result.add(x);
}
```
