# 主题配置说明

## 概述

项目使用 Tailwind CSS 进行样式管理，所有主题色都统一配置在 `tailwind.config.js` 中，便于维护和修改。

## 主题色系统

### 品牌色 (Brand Colors)

在 `tailwind.config.js` 中定义的品牌色：

```javascript
brand: {
  start: "#16d9e3",    // 渐变起始色
  middle: "#30c7ec",   // 渐变中间色
  end: "#46aef7",      // 渐变结束色
  light: "#e0f7fa",    // 浅色背景
  dark: "#0891b2",     // 深色变体
}
```

### 渐变背景

项目提供了三种预定义的渐变背景：

1. **主渐变** (`bg-gradient-brand`)

   - 方向：135 度对角线
   - 用途：按钮、图标背景、装饰元素

2. **反向渐变** (`bg-gradient-brand-reverse`)

   - 方向：225 度对角线
   - 用途：装饰背景、交替元素

3. **水平渐变** (`bg-gradient-brand-horizontal`)
   - 方向：水平（90 度）
   - 用途：文字渐变、标题

## 使用方法

### 1. 单色使用

```jsx
// 使用品牌色作为背景
<div className="bg-brand-start">...</div>

// 使用品牌色作为文字颜色
<span className="text-brand-middle">...</span>

// 使用品牌色作为边框
<div className="border-brand-end">...</div>
```

### 2. 渐变背景使用

```jsx
// 主渐变背景
<button className="bg-gradient-brand text-white">
  按钮
</button>

// 反向渐变背景
<div className="bg-gradient-brand-reverse">
  装饰元素
</div>

// 水平渐变（常用于文字）
<h1 className="bg-clip-text text-transparent bg-gradient-brand-horizontal">
  渐变标题
</h1>
```

### 3. 文字渐变效果

要实现文字渐变效果，需要组合使用三个类：

```jsx
<span className="bg-clip-text text-transparent bg-gradient-brand-horizontal">
  渐变文字
</span>
```

- `bg-clip-text`: 将背景裁剪到文字
- `text-transparent`: 使文字透明
- `bg-gradient-brand-horizontal`: 应用渐变背景

## 修改主题色

如果需要修改主题色，只需在 `tailwind.config.js` 中更新颜色值：

```javascript
// frontend/tailwind.config.js
theme: {
  extend: {
    colors: {
      brand: {
        start: "#YOUR_COLOR_1",
        middle: "#YOUR_COLOR_2",
        end: "#YOUR_COLOR_3",
        // ...
      },
    },
    backgroundImage: {
      'gradient-brand': 'linear-gradient(135deg, #YOUR_COLOR_1 0%, #YOUR_COLOR_2 47%, #YOUR_COLOR_3 100%)',
      // ...
    },
  },
}
```

修改后，所有使用这些变量的组件都会自动更新。

## 最佳实践

1. **优先使用 Tailwind 类名**：避免使用内联 `style` 属性
2. **保持一致性**：在整个项目中使用相同的渐变方向和色值
3. **语义化命名**：使用 `brand` 而不是具体的颜色名称，便于后期更换主题
4. **响应式设计**：结合 Tailwind 的响应式前缀使用（如 `md:bg-gradient-brand`）

## 示例

查看 `frontend/src/components/LandingPage.jsx` 了解完整的使用示例。

主要应用场景：

- 导航栏 Logo 和标题
- 英雄区标题和按钮
- 功能卡片图标
- CTA 按钮
- 页脚品牌标识
