# -*- coding: utf-8 -*-
#
# Copyright (C) 2007 Jeffrey Kyllo <jkyllo-eatlint@echospiral.com>
#
# Based on code from the Bitten project:
# Copyright (C) 2005-2007 Christopher Lenz <cmlenz@gmx.de>
# Copyright (C) 2007-2010 Edgewall Software
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://echospiral.com/trac/eatlint/wiki/License.

__docformat__ = 'restructuredtext en'

from trac.core import *
from trac.web.chrome import add_stylesheet, add_script
from bitten.api import IReportChartGenerator, IReportSummarizer


class PyLintChartGenerator(Component):
    implements(IReportChartGenerator)

    # IReportChartGenerator methods

    def get_supported_categories(self):
        return ['lint']

    def generate_chart_data(self, req, config, category):
        assert category == 'lint'

        db = self.env.get_db_cnx()
        cursor = db.cursor()

        #self.log.debug('config.name=\'%s\'' % (config.name,))
        query = """
select build.rev, 
 (select count(*) from bitten_report_item as item
  where item.report = report.id and item.name='category' and item.value='convention'),
 (select count(*) from bitten_report_item as item
  where item.report = report.id and item.name='category' and item.value='error'),
 (select count(*) from bitten_report_item as item
  where item.report = report.id and item.name='category' and item.value='refactor'),
 (select count(*) from bitten_report_item as item
  where item.report = report.id and item.name='category' and item.value='warning')
from bitten_report as report
 left outer join bitten_build as build ON (report.build=build.id)
where build.config='%s' and report.category='lint'
  and build.rev_time >= %s and build.rev_time <= %s
group by build.rev_time, build.rev, build.platform, report.id
order by build.rev_time;""" % (config.name, 
                               config.min_rev_time(self.env),
                               config.max_rev_time(self.env))

        #self.log.debug('sql=\'%s\'' % (query,))
        cursor.execute(query)

        lint = []
        prev_rev = None
        prev_counts = None

        for rev, conv, err, ref, warn in cursor:
            total = conv + err + ref + warn
            curr_counts = [rev, total, conv, err, ref, warn]
            if rev != prev_rev:
                lint.append(curr_counts)
            else:
                # cunningly / dubiously set rev = max(rev, rev) along with the counts
                lint[-1] = [max(prev, curr) for prev, curr in zip(curr_counts, lint[-1])]
                # recalculate total
                lint[-1][1] = sum(lint[-1][2:])
            prev_rev = rev

        data = {'title': 'Lint Problems by Type',
                'data': [
                    {'label': 'Total Problems', 'data': [[item[0], item[1]] for item in lint], 'lines': {'fill': True}},
                    {'label': 'Convention', 'data': [[item[0], item[2]] for item in lint]},
                    {'label': 'Error', 'data': [[item[0], item[3]] for item in lint]},
                    {'label': 'Refactor', 'data': [[item[0], item[4]] for item in lint]},
                    {'label': 'Warning', 'data': [[item[0], item[5]] for item in lint]},
                ],
                'options': {
                    'legend': {'position': 'sw', 'backgroundOpacity': 0.7},
                    'xaxis': {'tickDecimals': 0},
                    'yaxis': {'tickDecimals': 0},
                    'grid': { 'hoverable': 'true'},
                    'selection': {'mode': 'x'},
                },
               }

        return 'json.txt', {"json": data}


class PyLintSummarizer(Component):
    implements(IReportSummarizer)

    # IReportSummarizer methods

    def get_supported_categories(self):
        return ['lint']

    def render_summary(self, req, config, build, step, category):
        assert category == 'lint'
        add_stylesheet(req, 'bitten/bitten_lint.css')
        add_script(req, 'common/js/folding.js')
        add_script(req, 'bitten/bitten_lint.js')

        db = self.env.get_db_cnx()
        cursor = db.cursor()
        cursor.execute("""
SELECT item_type.value AS type, item_file.value AS file,
    item_line.value as line, item_category.value as category,
    item_msg.value as msg,
    report.category as report_category
FROM bitten_report AS report
 LEFT OUTER JOIN bitten_report_item AS item_type
  ON (item_type.report=report.id AND item_type.name='type')
 LEFT OUTER JOIN bitten_report_item AS item_file
  ON (item_file.report=report.id AND
    item_file.item=item_type.item AND
    item_file.name='file')
 LEFT OUTER JOIN bitten_report_item AS item_line
  ON (item_line.report=report.id AND
    item_line.item=item_type.item AND
    item_line.name='line')
 LEFT OUTER JOIN bitten_report_item AS item_category
  ON (item_category.report=report.id AND
    item_category.item=item_type.item AND
    item_category.name='category')
 LEFT OUTER JOIN bitten_report_item AS item_msg
  ON (item_msg.report=report.id AND
    item_msg.item=item_type.item AND
    item_msg.name='msg')
WHERE report.category='lint' AND build=%s AND step=%s
ORDER BY item_file.value, item_type.value""", (build.id, step.name))

        file_data = {}

        type_total = {}
        category_total = {'convention': 0, 'refactor': 0, 'warning': 0, 'error': 0}
        line_total = 0
        file_total = 0
        seen_files = {}

        for type, file, line, category, msg, report_category in cursor:
            if not file_data.has_key(file):
                file_data[file] = {'file': file, 'type': {}, 'lines': 0, 'category': {}, 'details': []}

            d = file_data[file]
            #d = {'type': type, 'line': line, 'category': category}
            if not d['type'].has_key(type):
                d['type'][type] = 0
            d['type'][type] += 1

            d['lines'] += 1
            line_total += 1

            if line is not None and line.isdigit():
                line = int(line)

            d['details'].append((
                    line is None and '??' or line,
                    type is None and '??' or type,
                    msg is None and '-' or msg))

            if not d['category'].has_key(category):
                d['category'][category] = 0
            d['category'][category] += 1

            if file:
                d['href'] = req.href.browser(config.path, file)

            if not type_total.has_key(type):
                type_total[type] = 0
            type_total[type] += 1

            if not category_total.has_key(category):
                category_total[category] = 0
            category_total[category] += 1

            if not seen_files.has_key(file):
                seen_files[file] = 0
                file_total += 1

        data = []
        for d in file_data.values():
            d['catnames'] = d['category'].keys()
            d['details'].sort()
            data.append(d)

        template_data = {}
        template_data['data'] = data
        template_data['totals'] = {'type': type_total, 'category': category_total, 'files': file_total, 'lines': line_total}

        return 'bitten_summary_lint.html', template_data
