from PyQt6.QtDesigner import QDesignerCustomWidgetInterface
from PyQt6.QtGui import QIcon

from airunner.widgets.generator_form.templates.generatorform_ui import Ui_generator_form

DOM_XML = """
<ui language="c++"> displayname="GeneratorFormWidget">
    <widget class="widgets::GeneratorFormWidget" name="generatorformwidget"/>
    <customwidgets>
        <customwidget>
            <class>widgets::GeneratorFormWidget</class>
            <addpagemethod>addPage</addpagemethod>
            <propertyspecifications>
                <stringpropertyspecification name="fileName" notr="true" type="singleline"/>
                <stringpropertyspecification name="text" type="richtext"/>
                <tooltip name="text">Explanatory text to be shown in Property Editor</tooltip>
            </propertyspecifications>
        </customwidget>
    </customwidgets>
</ui>
"""


class GeneratorFormPlugin(QDesignerCustomWidgetInterface):
    def name(self):
        return "GeneratorFormWidget"

    def group(self):
        return "AIRunner"

    def toolTip(self):
        return "AIRunner Generator Form Widget"

    def whatsThis(self):
        return "The generator form widget for AIRunner image generator tabs."

    def includeFile(self):
        return "generatorform"

    def icon(self):
        return QIcon()

    def isContainer(self):
        return False

    def createWidget(self):
        ui = Ui_generator_form()
        ui.setupUi(self)
        return ui

    def domXml(self):
        return DOM_XML
