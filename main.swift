import Cocoa
import WebKit

class WidgetWindow: NSWindow {
    override var canBecomeKey: Bool { true }
    override var canBecomeMain: Bool { false }
}


class DragHandleView: NSView {
    var initialMouseLocation: NSPoint = .zero
    var initialWindowOrigin: NSPoint = .zero

    func setup() {}

    override func draw(_ dirtyRect: NSRect) {
        // Subtle grip indicator
        NSColor(white: 1.0, alpha: 0.2).setFill()
        let cx = bounds.midX, cy = bounds.midY
        for dx in [-8.0, 0.0, 8.0] {
            NSBezierPath(ovalIn: NSRect(x: cx + CGFloat(dx) - 1.5, y: cy - 1.5, width: 3, height: 3)).fill()
        }
    }

    override func mouseDown(with event: NSEvent) {
        initialMouseLocation = NSEvent.mouseLocation
        initialWindowOrigin = window?.frame.origin ?? .zero
    }

    override func mouseDragged(with event: NSEvent) {
        guard let window = self.window else { return }
        let cur = NSEvent.mouseLocation
        window.setFrameOrigin(NSPoint(
            x: initialWindowOrigin.x + cur.x - initialMouseLocation.x,
            y: initialWindowOrigin.y + cur.y - initialMouseLocation.y))
    }

    override func resetCursorRects() {
        addCursorRect(bounds, cursor: .openHand)
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    var window: WidgetWindow!
    var webView: WKWebView!
    var statusItem: NSStatusItem!

    func applicationDidFinishLaunching(_ notification: Notification) {
        let frame = NSRect(x: 100, y: 100, width: 420, height: 750)
        window = WidgetWindow(
            contentRect: frame,
            styleMask: [.borderless, .resizable],
            backing: .buffered,
            defer: false
        )

        window.level = .normal
        window.hidesOnDeactivate = false
        window.collectionBehavior = [.managed, .fullScreenNone]
        window.isOpaque = false
        window.backgroundColor = .clear
        window.hasShadow = false
        window.isMovableByWindowBackground = false
        window.acceptsMouseMovedEvents = true
        window.title = "Stock Widget"
        window.setFrameAutosaveName("StockWidgetPosition")

        let config = WKWebViewConfiguration()
        config.preferences.setValue(true, forKey: "developerExtrasEnabled")
        webView = WKWebView(frame: window.contentView!.bounds, configuration: config)
        webView.autoresizingMask = [.width, .height]
        webView.setValue(false, forKey: "drawsBackground")

        let htmlPath = Bundle.main.resourcePath! + "/widget.html"
        let htmlURL = URL(fileURLWithPath: htmlPath)
        webView.loadFileURL(htmlURL, allowingReadAccessTo: htmlURL.deletingLastPathComponent())
        window.contentView?.addSubview(webView)

        let dragHandle = DragHandleView(frame: NSRect(
            x: 0, y: window.contentView!.bounds.height - 16,
            width: window.contentView!.bounds.width, height: 16))
        dragHandle.autoresizingMask = [.width, .minYMargin]
        dragHandle.setup()
        window.contentView?.addSubview(dragHandle)
        window.orderFront(nil)

        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        statusItem.button?.title = "📈"
        let menu = NSMenu()
        menu.addItem(NSMenuItem(title: "Show Widget", action: #selector(showWidget), keyEquivalent: ""))
        menu.addItem(NSMenuItem(title: "Hide Widget", action: #selector(hideWidget), keyEquivalent: ""))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Refresh Now", action: #selector(refreshData), keyEquivalent: "r"))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Quit", action: #selector(quitApp), keyEquivalent: "q"))
        statusItem.menu = menu
    }

    @objc func showWidget() { window.orderFront(nil) }
    @objc func hideWidget() { window.orderOut(nil) }
    @objc func refreshData() { webView.evaluateJavaScript("fetchData()", completionHandler: nil) }
    @objc func quitApp() { NSApp.terminate(nil) }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        window.orderFront(nil)
        return true
    }
}

let app = NSApplication.shared
app.setActivationPolicy(.accessory)
let delegate = AppDelegate()
app.delegate = delegate
app.run()
