# -*- mode: python -*-

block_cipher = None
binaries_a = [
   ('C:\\Windows\\SysWOW64\\libusb-1.0.dll', '.'),
]

a = Analysis(['Nu_ISP_Tool.py'],
             pathex=['C:\\Users\\jcliu\\Documents\\Visual Studio 2013\\Projects\\Nu_ISP_Tool\\Nu_ISP_Tool'],
             binaries=binaries_a,
             datas=[('C:\\Users\\jcliu\\Documents\\Visual Studio 2013\\Projects\\Nu_ISP_Tool\\Nu_ISP_Tool\\IMG\\company.png','IMG'),
			 ('C:\\Users\\jcliu\\Documents\\Visual Studio 2013\\Projects\\Nu_ISP_Tool\\Nu_ISP_Tool\\IMG\\icon.ico','IMG')
			 ],
             hiddenimports=['usb'],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='Nu_ISP_Tool',
          debug=False,
          strip=False,
          upx=False,
          nowindowed=True )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               name='Nu_ISP_Tool')