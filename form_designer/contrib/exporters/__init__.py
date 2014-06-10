from form_designer import settings
from form_designer.templatetags.friendly import friendly
from django.db.models import Count
from django.utils.translation import ugettext as _
from django.utils.encoding import smart_str


class ExporterBase(object):

    def __init__(self, model):
        self.model = model
        
    @staticmethod
    def is_enabled():
        return True 

    @staticmethod
    def export_format():
        raise NotImplemented()

    def init_writer(self):
        raise NotImplemented()

    def init_response(self):
        raise NotImplemented()
    
    def writerow(self, row):
        raise NotImplemented()

    def close(self):
        pass

    @classmethod
    def export_view(cls, modeladmin, request, queryset):
        return cls(modeladmin.model).export(request, queryset)

    def export(self, request, queryset=None):
        raise NotImplemented()


class FormLogExporterBase(ExporterBase):

    def export(self, request, queryset=None):
        self.init_response()
        self.init_writer()
        distinct_forms = queryset.aggregate(Count('form_definition', distinct=True))['form_definition__count']

        include_created = settings.CSV_EXPORT_INCLUDE_CREATED
        include_pk = settings.CSV_EXPORT_INCLUDE_PK
        include_header = settings.CSV_EXPORT_INCLUDE_HEADER
        include_form = settings.CSV_EXPORT_INCLUDE_FORM and distinct_forms > 1

        if queryset.count():
            if include_header:
                header = []
                if include_form:
                    header.append(_('Form'))
                if include_created:
                    header.append(_('Created'))
                if include_pk:
                    header.append(_('ID'))
                # Form fields might have been changed and not match 
                # existing form logs anymore.
                # Hence, use current form definition for header.
                # for field in queryset[0].data:
                #    header.append(field['label'] if field['label'] else field['key'])
                if distinct_forms == 1:
                    # Each field label is a header column
                    fields = queryset[0].form_definition.get_field_dict()
                    for field_name, field in fields.items():
                        header.append(field.label if field.label else field.key)
                else:
                    # Since multiple form types will most likely have different field labels,
                    # just have one 'Data' header column to display all the field labels and values
                    header.append(_('Data'))

                self.writerow([smart_str(cell, encoding=settings.CSV_EXPORT_ENCODING) for cell in header])

            for entry in queryset:
                row = []
                if include_form:
                    row.append(entry.form_definition)
                if include_created:
                    row.append(entry.created)
                if include_pk:
                    row.append(entry.pk)


                if distinct_forms == 1:
                    # Pretty print all values into their own corresponding columns
                    for item in entry.data:
                        value = friendly(item['value'], null_value=settings.CSV_EXPORT_NULL_VALUE, return_markup=False)
                        value = smart_str(value, encoding=settings.CSV_EXPORT_ENCODING)
                        row.append(value)
                else:
                    # Pretty print all values into the 'Data' column
                    value = u''
                    for item in entry.data:
                        value += item['label'] if item['label'] else item['name']
                        value += u': ' + friendly(item['value'], null_value=settings.CSV_EXPORT_NULL_VALUE, return_markup=False)
                        value += u'\n'

                    value = smart_str(value[:len(value)-1], encoding=settings.CSV_EXPORT_ENCODING)
                    row.append(value)

                self.writerow(row)

        self.close()
        return self.response
