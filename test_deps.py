import sys
print(f"Python Executable: {sys.executable}")
try:
    import bs4
    print("✅ bs4 is installed!")
    print(f"bs4 version: {bs4.__version__}")
except ImportError as e:
    print(f"❌ bs4 is NOT installed. Error: {e}")
    sys.exit(1)
