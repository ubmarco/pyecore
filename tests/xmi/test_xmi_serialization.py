import pytest
import os
from lxml import etree
import pyecore.ecore as Ecore
from pyecore.resources import *
from pyecore.resources.xmi import XMIResource, XMIOptions


@pytest.fixture(scope='module')
def lib():
    package = Ecore.EPackage('mypackage')
    package.nsURI = 'http://simplemetamodel/1.0'
    package.nsPrefix = 'simplemm'
    AbsA = Ecore.EClass('AbsA', abstract=True)
    A = Ecore.EClass('A', superclass=(AbsA,))
    SubA = Ecore.EClass('SubA', superclass=(A,))
    MyRoot = Ecore.EClass('MyRoot')
    MyRoot.a_container = Ecore.EReference('a_container', eType=AbsA, upper=-1,
                                          containment=True)
    MyRoot.eStructuralFeatures.append(MyRoot.a_container)
    package.eClassifiers.extend([MyRoot, A, SubA, AbsA])
    package.MyRoot = MyRoot
    package.SubA = SubA
    package.A = A
    # we register the metamodel first
    global_registry[package.nsURI] = package
    return package


def test_resource_createset(tmpdir, lib):
    f = tmpdir.mkdir('pyecore-tmp').join('test.xmi')
    resource = XMIResource(URI(str(f)))

    # we create some instances
    root = lib.MyRoot()
    a1 = lib.A()
    suba1 = lib.SubA()
    root.a_container.extend([a1, suba1])

    # we add the elements to the resource
    resource.append(root)
    resource.save()

    # we read the model
    resource = XMIResource(URI(str(f)))
    resource.load()
    assert resource.contents != []
    assert len(resource.contents[0].eContents) == 2


def test_resource_createSaveModifyRead(tmpdir, lib):
    f = tmpdir.mkdir('pyecore-tmp').join('test.xmi')
    resource = XMIResource(URI(str(f)))

    # we create some instances
    root = lib.MyRoot()
    a1 = lib.A()
    suba1 = lib.SubA()
    root.a_container.extend([a1, suba1])

    # we add the elements to the resource
    resource.append(root)
    resource.save()

    # we add more instances
    a2 = lib.A()
    root.a_container.append(a2)

    # we save again
    resource.save()

    # we read the model
    resource = XMIResource(URI(str(f)))
    resource.load()
    assert resource.contents != []
    assert len(resource.contents[0].eContents) == 3


eClass = Ecore.EPackage(name='test', nsURI='http://test/1.0',
                        nsPrefix='test')


@Ecore.EMetaclass
class A(object):
    name = Ecore.EAttribute('name', Ecore.EString)
    age = Ecore.EAttribute('age', Ecore.EInt)


def test_xmi_ecore_save_load(tmpdir):
    f = tmpdir.mkdir('pyecore-tmp').join('test.xmi')
    resource = XMIResource(URI(str(f)))

    resource.append(eClass)
    resource.save()

    resource = XMIResource(URI(str(f)))
    resource.load()
    root = resource.contents[0]
    assert root.name == 'test'
    assert root.getEClassifier('A') is not None


def test_xmi_ecore_save_option_xmitype(tmpdir):
    f = tmpdir.mkdir('pyecore-tmp').join('xmitype.xmi')
    resource = XMIResource(URI(str(f)))

    resource.append(eClass)
    resource.save(options={XMIOptions.OPTION_USE_XMI_TYPE: True})

    has_xmi_type = False
    with open(str(f)) as output:
        for line in output:
            if 'xmi:type="' in line:
                has_xmi_type = True
                break
    assert has_xmi_type

    resource.save()
    has_xmi_type = False
    with open(str(f)) as output:
        for line in output:
            if 'xmi:type="' in line:
                has_xmi_type = True
                break
    assert has_xmi_type is False


def test_xmi_ecore_save_heterogeneous_metamodel(tmpdir):
    f = tmpdir.mkdir('pyecore-tmp').join('heterogeneous.xmi')

    # Build a simple metamodel
    Root = Ecore.EClass('Root')
    Root.eStructuralFeatures.append(Ecore.EReference('element', Ecore.EObject))
    pack = Ecore.EPackage('mypack', nsURI='http://mypack/1.0',
                          nsPrefix='mypack_pref')
    pack.eClassifiers.append(Root)

    rset = ResourceSet()

    resource = rset.get_resource('tests/xmi/xmi-tests/My.ecore')
    root = resource.contents[0]
    rset.metamodel_registry[root.nsURI] = root

    # We open a first model with a special metamodel
    resource = rset.get_resource('tests/xmi/xmi-tests/MyRoot.xmi')
    root1 = resource.contents[0]

    r = Root(element=root1)
    resource = rset.create_resource(URI(str(f)))
    resource.append(r)
    resource.save()

    with open(str(f), 'r') as f:
        tree = etree.parse(f)
        xmlroot = tree.getroot()
        assert 'mypack_pref' in xmlroot.nsmap
        assert 'myprefix' in xmlroot.nsmap
