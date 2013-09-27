# Maintainer: William Adams <willadams+dev at gmail dot com>
pkgname=izdvd
pkgver=0.1.2
pkgrel=1
pkgdesc="A set of python scripts for authoring DVDs and/or DVD menus with little or no user interaction."
arch=('any')
url="https://pypi.python.org/pypi/izdvd"
license=('BSD')
groups=()
depends=('python' 'python-lxml' 'ffmpeg' 'imagemagick' 'dvdauthor' 
         'mjpegtools' 'mediainfo' 'toolame')
optdepends=('mplayer: for previewing videos/menus')
makedepends=()
provides=()
conflicts=()
replaces=()
backup=()
options=(!emptydirs)
source=('https://pypi.python.org/packages/source/i/izdvd/izdvd-0.1.2.tar.gz')
sha256sums=('09e3b4d2d2beaa0cdc6e1641839dd077081fb448bafdee9325618b8f0896b7d1')

package() {
  cd "$srcdir/$pkgname-$pkgver"
  python setup.py install --root="$pkgdir/" --optimize=1
  install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}

# vim:set ts=2 sw=2 et:

