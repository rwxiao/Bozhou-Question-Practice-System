# 页面指南检查记录

检查范围：渲染层、主题CSS、按钮、下拉框及控制器。规则来源：https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md 。

已修正：装饰图标隐藏于辅助技术；提供可聚焦的主要内容跳转；用户名关闭拼写检查；按钮 transition-all 改为明确属性；标题平衡换行；原生下拉框显式设置颜色与背景；主题切换同步 theme-color；长记录列表启用 content-visibility。

颜色检查：移动蓝主题主按钮、正文、辅助文字均达到4.5:1。保留可见键盘焦点、44px小屏按钮、48px提交按钮、减弱动画与弹窗滚动隔离。手机复查无横向溢出。

尚存建议（不属于本次配色修改）：

- frontend/src/surface.tsx:46 - 功能导航仍经按钮和控制器切换；建议迁移为真实链接并支持新标签打开。
- frontend/src/controller.js:45 - 启动固定到工作台，完整练习深链接和后退状态仍需路由改造。
- frontend/src/controller.js:42 - 服务端表单错误主要显示在提示区，建议字段级错误定位并提供提交中的进度指示。

本记录不宣称整个应用已满足完整无障碍标准。
