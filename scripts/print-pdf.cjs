// 用 Electron 隐藏窗口把 HTML 打印为 PDF（系统 CJK 字体，像素级渲染）
// 用法: node scripts/print-pdf.cjs <input.html> <output.pdf>
const { app, BrowserWindow } = require('electron')
const path = require('path')

const [input, output] = process.argv.slice(2)
if (!input || !output) {
  console.error('usage: node scripts/print-pdf.cjs <input.html> <output.pdf>')
  process.exit(1)
}

app.whenReady().then(async () => {
  const win = new BrowserWindow({ show: false, width: 900, height: 1200 })
  try {
    await win.loadFile(path.resolve(input))
    const pdf = await win.webContents.printToPDF({
      printBackground: true,
      pageSize: 'A4',
      margins: { marginType: 'default' },
    })
    require('fs').writeFileSync(path.resolve(output), pdf)
    console.log('PDF:', output, pdf.length, 'bytes')
    app.exit(0)
  } catch (err) {
    console.error('FAILED:', err.message)
    app.exit(1)
  }
})
