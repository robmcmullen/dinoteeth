#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# GuessIt - A library for guessing information from filenames
# Copyright (c) 2011 Nicolas Wack <wackou@gmail.com>
#
# GuessIt is free software; you can redistribute it and/or modify it under
# the terms of the Lesser GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# GuessIt is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Lesser GNU General Public License for more details.
#
# You should have received a copy of the Lesser GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from dinoteeth_test import *
from dinoteeth_mock import *

class TestBaseMetadata(TestCase):
    def setUp(self):
        self.imdb_obj = IMDbObject()
        self.imdb_obj['certificates'] = [u'Iceland:L', u'Portugal:M/12', u'Finland:S', u'Germany:6', u'Netherlands:AL', u'Spain:T', u'Sweden:7', u'UK:15', u'USA:PG-13', u'Canada:14::(Nova Scotia)', u'Australia:M']
        self.imdb_obj['runtimes'] = [u'95']
    
    def testCountryList(self):
        b = MockMetadata()
        cert = b.get_imdb_country_list(self.imdb_obj, 'certificates', "USA")
        self.assertEqual(cert, "PG-13")
        cert = b.get_imdb_country_list(self.imdb_obj, 'certificates', "UK")
        self.assertEqual(cert, "15")
        cert = b.get_imdb_country_list(self.imdb_obj, 'certificates', "Australia")
        self.assertEqual(cert, "M")
        runtime = b.get_imdb_country_list(self.imdb_obj, 'runtimes', "USA")
        self.assertEqual(runtime, u"95")
    
    def testForeignTitle1(self):
        b = MockMetadata()
        self.imdb_obj['akas'] = [u'OSS 117: Cairo, Nest of Spies::International (English title) (imdb display title), USA (imdb display title)', u'OSS 117 - Cairo: Nest of Spies::UK (DVD box title)', u'Agente 117::Brazil (imdb display title), Portugal (imdb display title)', u"Ajan 117 Kahire'de::Turkey (Turkish title) (DVD title)", u'OSS 117 - Apostoli sto Kairo::Greece (transliterated ISO-LATIN-1 title)', u'OSS 117 - Der Spion, der sich liebte::Germany (DVD title)', u'OSS 117: El Cairo nido de esp\xedas::Argentina (cable TV title)', u'OSS 117: El Cairo, nido de esp\xedas::Spain (imdb display title)', u'OSS 117: K\xe9ptelen k\xe9mreg\xe9ny::Hungary (imdb display title)']
        title = b.get_title(self.imdb_obj, "USA", "English")
        self.assertEqual(title, u"OSS 117: Cairo, Nest of Spies")
    
    def testForeignTitle2(self):
        b = MockMetadata()
        self.imdb_obj['akas'] =  [u'The Lives of Others::International (English title) (imdb display title), UK, USA', u'La vida de los otros::Argentina, Mexico (imdb display title), Peru (imdb display title), Spain', u'A Vida dos Outros::Brazil, Portugal', u'De andras liv::Finland (Swedish title), Sweden', u'A m\xe1sok \xe9lete::Hungary', u'Baskalarinin hayati::Turkey (Turkish title)', u'Chaiyim shel acherim::Israel (Hebrew title)', u'De andres liv::Denmark', u'De andres liv::Norway (imdb display title)', u'La vida dels altres::Spain (Catalan title)', u'La vie des autres::France', u'Le vite degli altri::Italy', u'Muiden el\xe4m\xe4::Finland', u'Oi zoes ton allon::Greece (transliterated ISO-LATIN-1 title)', u'Teiste elu::Estonia', u'Vietile altora::Romania (imdb display title)', u'Yoki hito no tame no sonata::Japan', u'Zivot drugih::Serbia (imdb display title)', u'Zivoty t\xfdch druh\xfdch::Slovakia', u'Zivoty tech druh\xfdch::Czech Republic', u'Zycie na podsluchu::Poland']
        title = b.get_title(self.imdb_obj, "USA", "English")
        self.assertEqual(title, u"The Lives of Others")
        title = b.get_title(self.imdb_obj, "Sweden", "Swedish")
        self.assertEqual(title, u"De andras liv")
        title = b.get_title(self.imdb_obj, "Finland", "Finnish")
        self.assertEqual(title, u"De andras liv")

    def testForeignTitle3(self):
        b = MockMetadata()
        self.imdb_obj['akas'] = [u'The Counterfeiters::Canada (English title), International (English title), UK, USA (new title)', u'Los falsificadores::Argentina, Mexico, Peru, Spain', u'Les faussaires::Belgium (French title), France', u'D\xe1blova d\xedlna::Czech Republic', u'Diablova dielna::Slovakia', u'F\xf6rfalskaren::Finland (Swedish title) (imdb display title)', u'Falsificatorii de bani::Romania (imdb display title)', u'Falsifikatori::Serbia (imdb display title)', u'Falskmyntarna::Sweden', u'Falskmyntnerne i Sachsenhausen::Norway (imdb display title)', u'Falszerze::Poland', u'Forfalskerne::Denmark', u'Il falsario::Italy', u'Kalpazanlar::Turkey (Turkish title)', u'Krivotvoritelji::Croatia', u'Os Fals\xe1rios::Brazil', u'Os Falsificadores::Portugal (imdb display title)', u'P\xe9nzhamis\xedt\xf3k::Hungary', u'Paraharaktes::Greece (transliterated ISO-LATIN-1 title)', u'V\xe4\xe4rent\xe4j\xe4::Finland']
        title = b.get_title(self.imdb_obj, "USA", "English")
        self.assertEqual(title, u"The Counterfeiters")

    def testForeignTitle4(self):
        b = MockMetadata()
        self.imdb_obj['akas'] = [u'Il re dei falsari::Italy', u'Money Money Money::', u'The Counterfeiters::UK', u'The Counterfeiters of Paris::USA', u'A balek bossz\xfaja::Hungary', u'De koning der valsmunters::Belgium (Flemish title)', u'Der Herr mit den Millionen::West Germany', u'Fachowiec z Caracas::Poland (imdb display title)', u'Falskmyntarna::Finland (Swedish title)', u'Le cave se rebiffe::Belgium (French title)', u'O paraharaktis::Greece (transliterated ISO-LATIN-1 title)', u'V\xe4\xe4r\xe4nrahantekij\xe4t::Finland']
        title = b.get_title(self.imdb_obj, "USA", "English")
        self.assertEqual(title, u"The Counterfeiters of Paris")
        title = b.get_title(self.imdb_obj, "Belgium", "Flemish")
        self.assertEqual(title, u"De koning der valsmunters")
        title = b.get_title(self.imdb_obj, "Belgium", "French")
        self.assertEqual(title, u"Le cave se rebiffe")

    def testCompleteTitle1(self):
        b = MockMetadata()
        self.imdb_obj['title'] = "The Train"
        self.imdb_obj['akas'] = [u'Il treno::Italy', u"John Frankenheimer's The Train::USA (complete title)", u'Le train::France', u'Der Zug::Austria, East Germany (imdb display title), West Germany', u'El tren::Argentina, Mexico, Spain', u'T\xe5get::Finland (Swedish title) (imdb display title), Sweden', u'A vonat::Hungary', u'Juna::Finland', u'O Comboio::Portugal', u'O Trem::Brazil', u'Pociag::Poland (imdb display title)', u'To traino::Greece (transliterated ISO-LATIN-1 title)', u'Toget::Norway', u'Toget::Denmark', u'Tren::Turkey (Turkish title)', u'Trenul::Romania', u'Vlak::Slovakia (imdb display title)', u'Vlak::Czech Republic (imdb display title)']
        title = b.get_title(self.imdb_obj, "USA", "English")
        self.assertEqual(title, u"The Train")

    def testPromotionalTitle1(self):
        b = MockMetadata()
        self.imdb_obj['title'] = "Toy Story 2"
        self.imdb_obj['akas'] = [u'Toy Story 2 in 3-D::USA (promotional title)', u'Toy Story 2::Argentina, Peru (imdb display title), Spain', u'\u0418\u0441\u0442\u043e\u0440\u0438\u044f \u0438\u0433\u0440\u0443\u0448\u0435\u043a 2::Russia', u'Histoire de jouets 2::Canada (French title)', u'Historia de juguetes 2::Mexico (informal literal title)', u'Lelulugu 2::Estonia (imdb display title)', u'Oyuncak hikayesi 2::Turkey (Turkish title)', u'Povestea jucariilor 2 3D::Romania (IMAX version)', u'Prica o igrackama 2::Croatia (imdb display title)', u'Prica o igrackama 2::Serbia (imdb display title)', u'Toy Story 2::Denmark', u'Toy Story 2::Greece (imdb display title)', u'Toy Story 2::Poland', u'Toy Story 2::Japan (English title)', u'Toy Story 2::France', u'Toy Story 2::Brazil', u'Toy Story 2 - Em Busca de Woody::Portugal', u'Toy Story 2: Pr\xedbeh hracek::Czech Republic', u'Toy story - J\xe1t\xe9kh\xe1bor\xfa 2.::Hungary (imdb display title)', u'Toy story 2 - Woody e Buzz alla riscossa::Italy', u'Toy story 2: Los juguetes vuelven a la carga::Spain', u'Tzatzooa Shel Sippur 2::Israel (Hebrew title)']
        title = b.get_title(self.imdb_obj, "USA", "English")
        self.assertEqual(title, u"Toy Story 2")

    def testPromotionalTitle2(self):
        b = MockMetadata()
        self.imdb_obj['title'] = "Toy Story 3"
        self.imdb_obj['akas'] = [u'3::USA (poster title)', u'Toy Story 3: An IMAX 3D Experience::USA (IMAX version)', u'Toy Story 3::Argentina (imdb display title), Mexico', u'\u0418\u0441\u0442\u043e\u0440\u0438\u044f \u0438\u0433\u0440\u0443\u0448\u0435\u043a: \u0411\u043e\u043b\u044c\u0448\u043e\u0439 \u043f\u043e\u0431\u0435\u0433::Russia', u'Histoire de jouets 3::Canada (French title) (dubbed version)', u'Lelulugu 3::Estonia', u'Oyuncak hikayesi 3::Turkey (Turkish title)', u'Povestea jucariilor 3::Romania', u'Prica o igrackama 3::Serbia (imdb display title)', u'Prica o igrackama 3::Croatia (imdb display title)', u'Rotallietu stasts 3::Latvia (imdb display title)', u'Toy Story 3::Denmark', u'Toy Story 3::Japan (English title)', u'Toy Story 3::Brazil (imdb display title)', u'Toy Story 3::Greece', u'Toy Story 3.::Hungary (imdb display title)', u'Toy Story 3: Pr\xedbeh hracek::Czech Republic (imdb display title)', u'Toy story 3::Spain', u'Toy story 3 - La grande fuga::Italy', u'Tzatzooa Shel Sippur 3::Israel (Hebrew title)', u'Wanju zong dongyuan 3::China (Mandarin title) (imdb display title)', u'Zaislu istorija 3::Lithuania (imdb display title)']
        title = b.get_title(self.imdb_obj, "USA", "English")
        self.assertEqual(title, u"Toy Story 3")

    def testRating1(self):
        b = MockMetadata()
        self.imdb_obj['certificates'] = [u'da:F::(Ontario)', u'Canada:G::(Manitoba/Nova Scotia/Quebec)', u'Ireland:G', u'Iceland:L', u'New Zealand:G', u'Mexico:AA', u'Malaysia:U', u'Hong Kong:I', u'USA:TV-G::(TV rating)', u'Argentina:Atp', u'Australia:G', u'Belgium:KT', u'Chile:TE', u'Denmark:7', u'Finland:S', u'France:U', u'Germany:o.Al.::(w)', u'Netherlands:AL', u'Norway:7', u'Peru:PT', u'Portugal:M/6', u'Singapore:G', u'South Korea:All', u'Spain:T', u'Sweden:7', u'UK:PG', u'USA:G', u'Greece:K', u'Brazil:Livre']
        certificate = b.get_imdb_country_list(self.imdb_obj, 'certificates', "USA", skip="TV rating")
        self.assertEqual(certificate, u"G")

if __name__ == '__main__':
    test_all()
